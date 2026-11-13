import json
import random
import sys
import requests
import tty
import termios
from type_effectiveness_cl import TypeEffectiveness


# pad or truncate a value so it occupies a fixed width
def format_string(text: str, length: int) -> str:
    text = str(text)

    if len(text) > length:
        return text[:length]  # cut if too long
    return text + " " * (length - len(text))  # pad with spaces if too short


# return foreground colored text
def print_rgb(r, g, b, text):
    color_code = f"\033[38;2;{r};{g};{b}m"
    reset_code = "\033[0m"

    if isinstance(text, list):  # return list of ANSI colored text, if list
        return [f"{color_code}{line}{reset_code}" for line in text]

    elif not isinstance(text, str):
        raise TypeError("text must be a string or a list of strings")

    return f"{color_code}{text}{reset_code}"


# receives 2 arrays, concatenates by each index (ref array 1 len()) and returns third
def arraysplice(array1, array2):
    if isinstance(array1, str):
        array1 = [array1]

    if isinstance(array2, str):
        array2 = [array2]

    max_len = max(len(array1), len(array2))
    result = []

    for i in range(max_len):
        s1 = array1[i] if i < len(array1) else ""
        s2 = array2[i] if i < len(array2) else ""
        result.append(s1 + " " + s2)

    return result


# receives array of strings, prints them
def arrayprint(array, color=None):
    for i in array:
        print(i)


def llm_access_tev(battlecontext, moves):
    URL = "http://192.168.5.8:9401/v1/systemone"

    options = {
        f"move_{i}": {
            "name": move["name"],
            "description": (
                f'{move["name"]}: {move["type"]} type, '
                f'power {move["power"]}, '
            ),
        }
        for i, move in enumerate(moves)
    }

    payload = {
        "model": "tev1:4b",
        "state": {
            "battle": battlecontext,
            "available_moves": options,
        },
        "questions": {
            "best_move": {
                "type": "choice",
                "instructions": (
                    "Which available move is most likely to produce "
                    "the best battle outcome? Consider the battle_history" 
                    "type effectiveness, damage and current battle state. "
                ),
                "criteria": {
                    key: value["description"]
                    for key, value in options.items()
                },
            }
        },
        "keep_alive": -1,
    }

    response = requests.post(URL, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    pretty_result = json.dumps(result, indent=4)

    return pretty_result


class BattleProcedure:
    MAJOR_STATUSES = {"paralysis", "burn", "poison", "bad_poison", "freeze", "sleep"}

    STATUS_IMMUNITIES = {
        "burn": {"Fire"},
        "paralysis": {"Electric"},
        "poison": {"Poison", "Steel"},
        "bad_poison": {"Poison", "Steel"},
        "freeze": {"Ice"},
    }

    STATUS_MESSAGES = {
        "paralysis": "was paralyzed! It may be unable to move!",
        "burn": "was burned!",
        "poison": "was poisoned!",
        "bad_poison": "was badly poisoned!",
        "freeze": "was frozen solid!",
        "sleep": "fell asleep!",
    }

    STAT_LABELS = {
        "spc_attack": "Attack",
        "defence": "Defense",
        "spc_defence": "Sp. Def",
        "speed": "Speed",
    }

    # Effects that act on the user rather than the target.
    SELF_TARGET_EFFECTS = {
        "self-debuff", "atk_up", "sp_boost", "heal", "recoil", "protect", "switch",
    }

    def __init__(self, p1, p2, usermode, botmode, userds_pokemon, botds_pokemon, actionlog=None):
        self.p1 = p1
        self.p2 = p2
        self.usermode = usermode
        self.botmode = botmode
        self.userds_pokemon = userds_pokemon
        self.botds_pokemon = botds_pokemon
        self.actionlog = actionlog if actionlog is not None else []

        self.effect_handlers = {
            "paralysis": self.effect_apply_status,
            "burn": self.effect_apply_status,
            "poison": self.effect_apply_status,
            "bad_poison": self.effect_apply_status,
            "freeze": self.effect_apply_status,
            "sleep": self.effect_apply_status,
            "sp_def_down": self.effect_sp_def_down,
            "sp_atk_down": self.effect_sp_atk_down,
            "flinch": self.effect_flinch,
            "self-debuff": self.effect_self_debuff,
            "atk_up": self.effect_atk_up,
            "sp_boost": self.effect_sp_boost,
            "heal": self.effect_heal,
            "recoil": self.effect_recoil,
            "protect": self.effect_protect,
            "switch": self.effect_switch,
        }

    # --- status helpers ----------------------------------------------

    def status_list(self, pokemon):
        return pokemon.setdefault("status", [])

    def has_status(self, pokemon, name):
        return name in pokemon.get("status", [])

    def remove_status(self, pokemon, name):
        if name in pokemon.get("status", []):
            pokemon["status"].remove(name)

    def volatile(self, pokemon):
        return pokemon.setdefault("volatile", {})

    def stat_stages(self, pokemon):
        return pokemon.setdefault("stat_stages", {})

    def log_event(self, player, event, hp):
        self.actionlog.append({
            "player": player,
            "event": event,
            "hp": hp,
        })

    def stat_multiplier(self, stage):
        stage = max(-6, min(6, stage))
        if stage >= 0:
            return (2 + stage) / 2
        return 2 / (2 - stage)

    def effective_stat(self, pokemon, stat):
        value = pokemon[stat] * self.stat_multiplier(self.stat_stages(pokemon).get(stat, 0))

        # Paralysis halves speed.
        if stat == "speed" and self.has_status(pokemon, "paralysis"):
            value *= 0.5

        return value

    def change_stat(self, pokemon, stat, amount):
        stages = self.stat_stages(pokemon)
        old = stages.get(stat, 0)
        new = max(-6, min(6, old + amount))
        stages[stat] = new

        if new == old:
            print(f"{pokemon['name']}'s {self.STAT_LABELS[stat]} won't go any "
                  f"{'higher' if amount > 0 else 'lower'}!")
            return

        direction = "rose" if amount > 0 else "fell"
        if abs(amount) >= 2:
            direction = "sharply " + direction

        print(f"{pokemon['name']}'s {self.STAT_LABELS[stat]} {direction}!")
        self.log_event(pokemon["name"], f"{self.STAT_LABELS[stat]} {direction}", pokemon["health"])

    def can_apply_status(self, target, name):
        # A Pokemon can only carry one major status condition at a time.
        if name in self.MAJOR_STATUSES:
            if any(s in self.MAJOR_STATUSES for s in target.get("status", [])):
                return False

        # Type immunities (Fire can't burn, Electric can't paralyze, etc.)
        target_types = set(target["type"].split("/"))
        if target_types & self.STATUS_IMMUNITIES.get(name, set()):
            print(f"It doesn't affect {target['name']}...")
            return False

        return True

    def apply_status(self, target, name):
        if not self.can_apply_status(target, name):
            return False

        self.status_list(target).append(name)

        if name == "bad_poison":
            target.setdefault("status_turns", {})["bad_poison"] = 1
        elif name == "sleep":
            target.setdefault("status_turns", {})["sleep"] = random.randint(1, 3)

        print(f"{target['name']} {self.STATUS_MESSAGES[name]}")
        self.log_event(target["name"], self.STATUS_MESSAGES[name], target["health"])
        return True

    # --- effect handlers ---------------------------------------------

    def effect_apply_status(self, attacker, defender, move, damage):
        self.apply_status(defender, move["effect"]["status"])

    def effect_sp_def_down(self, attacker, defender, move, damage):
        self.change_stat(defender, "spc_defence", -1)

    def effect_sp_atk_down(self, attacker, defender, move, damage):
        self.change_stat(defender, "spc_attack", -1)

    def effect_flinch(self, attacker, defender, move, damage):
        # Only bites if the target has not moved yet this turn.
        self.volatile(defender)["flinch"] = True

    def effect_self_debuff(self, attacker, defender, move, damage):
        self.change_stat(attacker, "defence", -1)
        self.change_stat(attacker, "spc_defence", -1)

    def effect_atk_up(self, attacker, defender, move, damage):
        self.change_stat(attacker, "spc_attack", 2)  # "sharply raises"

    def effect_sp_boost(self, attacker, defender, move, damage):
        self.change_stat(attacker, "spc_attack", 1)
        self.change_stat(attacker, "spc_defence", 1)

    def effect_heal(self, attacker, defender, move, damage):
        healed = min(
            attacker["max_health"] - attacker["health"],
            max(1, attacker["max_health"] // 2),
        )

        if healed <= 0:
            print(f"{attacker['name']}'s HP is already full!")
            return

        attacker["health"] += healed
        print(f"{attacker['name']} recovered {healed} HP!")
        self.log_event(attacker["name"], f"recovered {healed} HP", attacker["health"])

    def effect_recoil(self, attacker, defender, move, damage):
        recoil = max(1, damage // 3)
        attacker["health"] = max(0, attacker["health"] - recoil)
        print(f"{attacker['name']} was hurt by recoil! ({recoil} damage)")
        self.log_event(attacker["name"], f"recoil ({recoil} damage)", attacker["health"])

    def effect_protect(self, attacker, defender, move, damage):
        self.volatile(attacker)["protect"] = True
        print(f"{attacker['name']} protected itself!")
        self.log_event(attacker["name"], "protected itself", attacker["health"])

    def effect_switch(self, attacker, defender, move, damage):
        self.volatile(attacker)["switch_out"] = True
        print(f"{attacker['name']} is ready to switch out!")
        self.log_event(attacker["name"], "prepared to switch out", attacker["health"])

    def apply_move_effect(self, attacker, defender, move, damage=0):
        effect = move.get("effect") or {}
        status = effect.get("status")

        # Passive properties (priority, high_crit, sure_hit) are handled
        # by determine_order / move_hits / calculate_damage instead.
        if not status or status not in self.effect_handlers:
            return

        # Self-targeting effects always resolve.
        if status in self.SELF_TARGET_EFFECTS:
            self.effect_handlers[status](attacker, defender, move, damage)
            return

        # Opponent-targeting effects roll their chance.
        if random.randint(1, 100) > effect.get("chance", 0):
            return

        self.effect_handlers[status](attacker, defender, move, damage)

    # --- turn handling -----------------------------------------------

    def skip_turn(self, pokemon, reason):
        print(f"{pokemon['name']} {reason}")
        self.log_event(pokemon["name"], reason, pokemon["health"])
        return False

    def can_move(self, pokemon):
        if self.volatile(pokemon).get("flinch"):
            self.volatile(pokemon)["flinch"] = False
            return self.skip_turn(pokemon, "flinched and couldn't move!")

        if self.has_status(pokemon, "freeze"):
            if random.random() < 0.2:
                self.remove_status(pokemon, "freeze")
                print(f"{pokemon['name']} thawed out!")
            else:
                return self.skip_turn(pokemon, "is frozen solid!")

        if self.has_status(pokemon, "sleep"):
            turns = pokemon.setdefault("status_turns", {})
            turns["sleep"] = turns.get("sleep", random.randint(1, 3))

            if turns["sleep"] <= 0:
                self.remove_status(pokemon, "sleep")
                turns.pop("sleep", None)
                print(f"{pokemon['name']} woke up!")
            else:
                turns["sleep"] -= 1
                return self.skip_turn(pokemon, "is fast asleep!")

        if self.has_status(pokemon, "paralysis") and random.random() < 0.25:
            return self.skip_turn(pokemon, "is fully paralyzed!")

        return True

    def apply_end_of_turn(self, pokemon):
        if pokemon["health"] <= 0:
            return

        if self.has_status(pokemon, "burn"):
            damage = max(1, pokemon["max_health"] // 16)
            pokemon["health"] = max(0, pokemon["health"] - damage)
            print(f"{pokemon['name']} was hurt by its burn! ({damage} damage)")
            self.log_event(pokemon["name"], f"burn ({damage} damage)", pokemon["health"])

        if self.has_status(pokemon, "poison"):
            damage = max(1, pokemon["max_health"] // 8)
            pokemon["health"] = max(0, pokemon["health"] - damage)
            print(f"{pokemon['name']} was hurt by poison! ({damage} damage)")
            self.log_event(pokemon["name"], f"poison ({damage} damage)", pokemon["health"])

        if self.has_status(pokemon, "bad_poison"):
            turns = pokemon.setdefault("status_turns", {})
            counter = turns.get("bad_poison", 1)
            damage = max(1, (pokemon["max_health"] * counter) // 16)
            pokemon["health"] = max(0, pokemon["health"] - damage)
            turns["bad_poison"] = counter + 1
            print(f"{pokemon['name']} was hurt by poison! ({damage} damage)")
            self.log_event(pokemon["name"], f"bad poison ({damage} damage)", pokemon["health"])

        if pokemon["health"] <= 0:
            print(f"{pokemon['name']} fainted!")

    def switch_active(self, pokemon, team):
        bench = [p for p in team if p["health"] > 0 and p is not pokemon]

        if not bench:
            print(f"{pokemon['name']} has no one to switch to!")
            return False

        print(f"{pokemon['name']} switched out!")
        self.log_event(pokemon["name"], "switched out", pokemon["health"])

        # Stat changes are lost when a Pokemon leaves the field.
        pokemon["stat_stages"] = {}

        if any(p is pokemon for p in team):
            team[:] = [p for p in team if p is not pokemon] + [pokemon]

        return True

    def calculate_damage(self, attacker, defender, move):
        level = 50

        if move["category"] == "Special":
            attack_stat = self.effective_stat(attacker, "spc_attack")
            defence_stat = self.effective_stat(defender, "spc_defence")
        else:
            attack_stat = self.effective_stat(attacker, "spc_attack")

            # Burn halves physical attack.
            if self.has_status(attacker, "burn"):
                attack_stat *= 0.5

            defence_stat = self.effective_stat(defender, "defence")

        base_damage = (
            (((2 * level / 5 + 2) *
            move["power"] *
            attack_stat /
            defence_stat) / 50)
            + 2
        )

        # STAB
        stab = 1.5 if move["type"] == attacker["type"] else 1.0

        # Type effectiveness
        effectiveness = TypeEffectiveness.multiplier(
            move["type"],
            defender["type"]
        )

        # Critical hit (high-crit moves have double the usual ratio)
        crit_chance = 0.125 if (move.get("effect") or {}).get("status") == "high_crit" else 0.0625
        critical = 1.5 if random.random() < crit_chance else 1.0

        # Random factor (85%-100%)
        random_modifier = random.uniform(0.85, 1.0)

        modifier = (
            stab *
            effectiveness *
            critical *
            random_modifier
        )

        damage = int(base_damage * modifier)

        return max(1, damage), effectiveness, critical > 1

    def move_hits(self, move):
        effect = move.get("effect") or {}

        # "Never misses" moves and self-targeting status moves (accuracy 0).
        if effect.get("status") == "sure_hit" or move["accuracy"] <= 0:
            return True

        return random.randint(1, 100) <= move["accuracy"]

    def use_move(self, attacker, defender, move, player):
        print(f"{attacker['name']} used {move['name']}!")

        effect_status = (move.get("effect") or {}).get("status")
        targets_self = effect_status in self.SELF_TARGET_EFFECTS

        # Protect only blocks moves aimed at the protecting Pokemon.
        if not targets_self and self.volatile(defender).get("protect"):
            print(f"{defender['name']} protected itself!")

            self.actionlog.append({
                "player": attacker['name'],
                "move": move["name"],
                "damage": "protected",
                f"{attacker['id']}_hp": attacker["health"],
                f"{defender['id']}_hp": defender["health"]
            })

            return

        # Move missed
        if not self.move_hits(move):
            print("But it missed!")

            self.actionlog.append({  # append action with miss
                "player": attacker['name'],
                "move": move["name"],
                "damage": "miss",
                f"{attacker['id']}_hp": attacker["health"],
                f"{defender['id']}_hp": defender["health"]
            })

            return

        # Status moves (power 0) apply their effect but deal no damage.
        if move["power"] <= 0:
            self.actionlog.append({
                "player": attacker['name'],
                "move": move["name"],
                "damage": 0,
                f"{attacker['id']}_hp": attacker["health"],
                f"{defender['id']}_hp": defender["health"]
            })

            self.apply_move_effect(attacker, defender, move, 0)
            return

        # Store HP before damage
        health_before = defender["health"]

        damage, effectiveness, critical = self.calculate_damage(
            attacker,
            defender,
            move
        )

        defender["health"] -= damage
        defender["health"] = max(0, defender["health"])

        # Store the move and its effect on health
        self.actionlog.append({
            "player": attacker['name'],
            "move": move["name"],
            "damage": damage,
            f"{attacker['id']}_hp": attacker["health"],
            f"{defender['id']}_hp": defender["health"]
        })

        print(f"It dealt {damage} damage!")

        if critical:
            print("A critical hit!")

        if effectiveness > 1:
            print("It's super effective!")

        elif effectiveness < 1 and effectiveness > 0:
            print("It's not very effective...")

        elif effectiveness == 0:
            print("It had no effect!")

        # Secondary effects do not trigger on immune targets.
        if effectiveness > 0:
            self.apply_move_effect(attacker, defender, move, damage)

        if defender["health"] <= 0:
            print(f"{defender['name']} fainted!")

    def determine_order(self, p1, move1, p2, move2):

        if move1["priority"] > move2["priority"]:
            return [(p1, move1), (p2, move2)]

        if move2["priority"] > move1["priority"]:
            return [(p2, move2), (p1, move1)]

        if self.effective_stat(p1, "speed") > self.effective_stat(p2, "speed"):
            return [(p1, move1), (p2, move2)]

        if self.effective_stat(p2, "speed") > self.effective_stat(p1, "speed"):
            return [(p2, move2), (p1, move1)]

        if random.random() < 0.5:
            return [(p1, move1), (p2, move2)]

        return [(p2, move2), (p1, move1)]

    # --- interfaces ---------------------------------------------------

    def interface_pkmnlist(self, cur_pkmn, ds_pokemon):
        pkmncount = sum(item["health"] <= 0 for item in ds_pokemon)
        pkmnlen = len(ds_pokemon)
        left = pkmnlen - pkmncount
        form = "o" * left
        form += "x" * pkmncount
        form += f" {cur_pkmn['name']}"

        statuses = cur_pkmn.get("status", [])
        if statuses:
            form += f" [{'/'.join(statuses)}]"

        return form

    def interface_healthbar(self, botds):
        bot_hpercent = (botds["health"] / botds["max_health"]) * 100
        bot_hblocks = int(round(bot_hpercent / 5))

        bot_hblocks = max(0, min(20, bot_hblocks))

        form = (
            f"{botds['health']}/{botds['max_health']} ["
            + ("■" * bot_hblocks + " " * (20 - bot_hblocks))
            + "]"
        )

        return form

    def interface(self, p1, p2, userds_pokemon, botds_pokemon, size):
        print("")

        if size == 1:
            length = 80
            print('/' * length)

            statusbar1 = self.interface_pkmnlist(p1, userds_pokemon)
            statusbar2 = self.interface_pkmnlist(p2, botds_pokemon)

            statusbar = f"{statusbar1}"
            statusbar += ' ' * (
                length - (len(statusbar1) + len(statusbar2))
            )
            statusbar += f"{statusbar2}"

            print(statusbar)

            bar1 = self.interface_healthbar(p1)
            bar2 = self.interface_healthbar(p2)

            healthbar = f"{bar1}"
            healthbar += ' ' * (length - (len(bar1) + len(bar2)))
            healthbar += f"{bar2}"

            print(healthbar)
            print("")

    # fancy ANSI version
    def moveselection_interface_ansi(self, move_ds):
        def get_key():
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)
                key = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            return key

        structured_array = []
        for index in move_ds:  # each move option gets a square
            line = []

            line.append('─' * 26)
            line.append(f"| {format_string(index['name'],23)}|")
            line.append(f"| {format_string(index['type'],12)} pp: {format_string(index['pp'],6)}|")
            line.append(f"| pwr: {format_string(index['power'],7)} acc: {format_string(index['accuracy'],5)}|")
            line.append('─' * 26)

            structured_array.append(line)

        #print("Press Selection ←→↑↓ ")
        #interfacearray = arraysplice(structured_array[0],structured_array[1]) + arraysplice(structured_array[2],structured_array[3])
        #arrayprint(interfacearray)

        print("Press WASD, q to quit")

        # Save cursor position here
        print("\033[s", end="")

        while True:
            key = get_key()

            if key == 'q':
                break

            # Return to the exact position where the display starts
            print("\033[u", end="")

            # Clear the old display
            print("\033[J", end="")

            if key == 'A':
                arrayprint(
                    arraysplice(print_rgb(250, 0, 0, structured_array[0]),structured_array[1]
                ))
                arrayprint(
                    arraysplice(structured_array[2],structured_array[3]
                ))

            elif key == 'B':
                arrayprint(
                    arraysplice(structured_array[0],structured_array[1]
                ))
                arrayprint(
                    arraysplice(structured_array[2],print_rgb(250, 0, 0, structured_array[3])
                ))

            elif key == 'C':
                arrayprint(
                    arraysplice(structured_array[0],print_rgb(250, 0, 0, structured_array[1])
                ))
                arrayprint(
                    arraysplice(structured_array[2],structured_array[3]
                ))

            elif key == 'D':
                arrayprint(
                    arraysplice(structured_array[0],structured_array[1]
                ))
                arrayprint(
                    arraysplice(print_rgb(250, 0, 0, structured_array[2]),structured_array[3]
                ))

    # shit version
    def moveselection_interface(self, move_ds):
        while True:
            structured_array = []
            count = 1
            for index in move_ds:
                line = []

                line.append('─' * 26)
                line.append(f"| {format_string(index['name'],20)} {count} |")
                line.append(f"| {format_string(index['type'],12)} pp: {format_string(index['pp'],6)}|")
                line.append(f"| pwr: {format_string(index['power'],7)} acc: {format_string(index['accuracy'],5)}|")
                line.append('─' * 26)

                structured_array.append(line)
                count += 1

            arrayprint(arraysplice(structured_array[0],structured_array[1]))
            arrayprint(arraysplice(structured_array[2],structured_array[3]))

            opt = int(input("option: "))
            if opt in range(1, len(move_ds)):
                return move_ds[opt - 1]  # array index
            else:
                print("Error not in range")

    # --- battle -------------------------------------------------------

    def _result(self, switched=False):
        p1 = self.p1
        p2 = self.p2
        winner = None

        if p1["health"] <= 0:
            print(f"{p2['name']} wins!\n")
            winner = "p2"

        elif p2["health"] <= 0:
            print(f"{p1['name']} wins!\n")
            winner = "p1"

        return {
            "p1": p1,
            "p2": p2,
            "winner": winner,
            "switched": switched,
            "actionlog": self.actionlog,
        }

    def run_round(self):
        """Resolve a single turn for the two active Pokemon."""
        p1 = self.p1
        p2 = self.p2
        usermode = self.usermode
        botmode = self.botmode
        userds_pokemon = self.userds_pokemon
        botds_pokemon = self.botds_pokemon

        # Make sure both combatants have the fields the status system needs.
        for pokemon in (p1, p2):
            pokemon.setdefault("max_health", pokemon["health"])
            pokemon.setdefault("status", [])
            pokemon.setdefault("volatile", {})
            pokemon.setdefault("stat_stages", {})
            pokemon.setdefault("status_turns", {})

        """ example of tev return json:
        {
            "model": "tev1:4b",
            "answers": {
                "best_move": {
                    "type": "choice",
                    "choice": "move_0",
                    "probabilities": {
                        "move_0": 0.8938478298241374,
                        "move_1": 0.04450206301392114,
                        "move_2": 0.026991865638406776,
                        "move_3": 0.03465824152353479
                    },
                    "confidence": 0.6733473442227729
                }
            },
            "usage": {
                "input_tokens": 373,
                "output_tokens": 0
            },
            "prompt_eval_cached_count": 373
        }
        """

        self.interface(
            p1,
            p2,
            userds_pokemon,
            botds_pokemon,
            1
        )

        if usermode == "random":
            move1 = random.choice(p1["moves"])

        elif usermode == "user":
            move1 = self.moveselection_interface_ansi(p1["moves"])

        elif usermode == "ai":
            context = {
                "your_pokemon": p1["name"],
                "opponent": p2["name"],
                "your_hp_percent": p1["health"],
                "opponent_hp_percent": p2["health"],
                "battle_history": self.actionlog
            }
            result = llm_access_tev(context, p1["moves"])
            #print(result)
            result = json.loads(result)
            move1 = result["answers"]["best_move"]["choice"]  # extract json value
            index = int(move1[-1])  # parse out index at end of move_{} string
            move1 = p1["moves"][index]  # map to moves

        if botmode == "random":
            move2 = random.choice(p2["moves"])

        elif botmode == "user":
            move2 = self.moveselection_interface_ansi(p2["moves"])

        elif botmode == "ai":
            context = {
                "your_pokemon": p2["name"],
                "opponent": p1["name"],
                "your_hp_percent": p2["health"],
                "opponent_hp_percent": p1["health"],
                "battle_history": self.actionlog
            }
            result = llm_access_tev(context, p1["moves"])
            #print(result)
            result = json.loads(result)
            move2 = result["answers"]["best_move"]["choice"]
            index = int(move2[-1])
            move2 = p2["moves"][index]

        order = self.determine_order(
            p1, move1,
            p2, move2
        )

        first_pokemon, first_move = order[0]
        second_pokemon, second_move = order[1]

        # Determine which player is acting
        first_player = "p1" if first_pokemon == p1 else "p2"

        target = p2 if first_pokemon == p1 else p1

        if self.can_move(first_pokemon):
            self.use_move(
                first_pokemon,
                target,
                first_move,
                first_player
            )

        if target["health"] <= 0:
            return self._result()

        # Determine which player is acting
        second_player = "p1" if second_pokemon == p1 else "p2"

        target = p2 if second_pokemon == p1 else p1

        if self.can_move(second_pokemon):
            self.use_move(
                second_pokemon,
                target,
                second_move,
                second_player
            )

        # End-of-turn status damage (burn, poison, bad poison)
        self.apply_end_of_turn(p1)
        self.apply_end_of_turn(p2)

        if p1["health"] <= 0 or p2["health"] <= 0:
            return self._result()

        # One-turn effects expire at the end of the turn.
        self.volatile(p1).pop("protect", None)
        self.volatile(p1).pop("flinch", None)
        self.volatile(p2).pop("protect", None)
        self.volatile(p2).pop("flinch", None)

        print(f"{p1['name']}: {p1['health']}/{p1['max_health']} HP")

        print(f"{p2['name']}: {p2['health']}/{p2['max_health']} HP")

        # U-turn / Volt Switch: end this matchup so the outer loop can
        # bring in the next available Pokemon.
        switched = False

        if self.volatile(p1).get("switch_out"):
            self.volatile(p1).pop("switch_out", None)
            switched = self.switch_active(p1, userds_pokemon) or switched

        if self.volatile(p2).get("switch_out"):
            self.volatile(p2).pop("switch_out", None)
            switched = self.switch_active(p2, botds_pokemon) or switched

        return self._result(switched)

    def run(self):
        """Resolve turns until a Pokemon faints or a switch ends the matchup."""
        while self.p1["health"] > 0 and self.p2["health"] > 0:
            result = self.run_round()

            if result["switched"] or result["winner"] is not None:
                return result

        return self._result()
