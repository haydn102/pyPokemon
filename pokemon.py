import json
import sys
import time
import random
# for keyboard stuff
import sys
import tty
import termios


ds_allmoves         = []
ds_allpokemon       = []
userds_pokemon      = [] # includes moves
botds_pokemon       = []

TYPE_EFFECTIVENESS = {

    # Normal
    ("Normal", "Rock"): 0.5,
    ("Normal", "Ghost"): 0.0,
    ("Normal", "Steel"): 0.5,

    # Fire
    ("Fire", "Fire"): 0.5,
    ("Fire", "Water"): 0.5,
    ("Fire", "Grass"): 2.0,
    ("Fire", "Ice"): 2.0,
    ("Fire", "Bug"): 2.0,
    ("Fire", "Rock"): 0.5,
    ("Fire", "Dragon"): 0.5,
    ("Fire", "Steel"): 2.0,

    # Water
    ("Water", "Fire"): 2.0,
    ("Water", "Water"): 0.5,
    ("Water", "Grass"): 0.5,
    ("Water", "Ground"): 2.0,
    ("Water", "Rock"): 2.0,
    ("Water", "Dragon"): 0.5,

    # Electric
    ("Electric", "Water"): 2.0,
    ("Electric", "Electric"): 0.5,
    ("Electric", "Grass"): 0.5,
    ("Electric", "Ground"): 0.0,
    ("Electric", "Flying"): 2.0,
    ("Electric", "Dragon"): 0.5,

    # Grass
    ("Grass", "Fire"): 0.5,
    ("Grass", "Water"): 2.0,
    ("Grass", "Grass"): 0.5,
    ("Grass", "Poison"): 0.5,
    ("Grass", "Ground"): 2.0,
    ("Grass", "Flying"): 0.5,
    ("Grass", "Bug"): 0.5,
    ("Grass", "Rock"): 2.0,
    ("Grass", "Dragon"): 0.5,
    ("Grass", "Steel"): 0.5,

    # Ice
    ("Ice", "Fire"): 0.5,
    ("Ice", "Water"): 0.5,
    ("Ice", "Grass"): 2.0,
    ("Ice", "Ground"): 2.0,
    ("Ice", "Flying"): 2.0,
    ("Ice", "Dragon"): 2.0,
    ("Ice", "Steel"): 0.5,
    ("Ice", "Ice"): 0.5,

    # Fighting
    ("Fighting", "Normal"): 2.0,
    ("Fighting", "Ice"): 2.0,
    ("Fighting", "Poison"): 0.5,
    ("Fighting", "Flying"): 0.5,
    ("Fighting", "Psychic"): 0.5,
    ("Fighting", "Bug"): 0.5,
    ("Fighting", "Rock"): 2.0,
    ("Fighting", "Ghost"): 0.0,
    ("Fighting", "Dark"): 2.0,
    ("Fighting", "Steel"): 2.0,
    ("Fighting", "Fairy"): 0.5,

    # Poison
    ("Poison", "Grass"): 2.0,
    ("Poison", "Poison"): 0.5,
    ("Poison", "Ground"): 0.5,
    ("Poison", "Rock"): 0.5,
    ("Poison", "Ghost"): 0.5,
    ("Poison", "Steel"): 0.0,
    ("Poison", "Fairy"): 2.0,

    # Ground
    ("Ground", "Fire"): 2.0,
    ("Ground", "Electric"): 2.0,
    ("Ground", "Grass"): 0.5,
    ("Ground", "Poison"): 2.0,
    ("Ground", "Flying"): 0.0,
    ("Ground", "Bug"): 0.5,
    ("Ground", "Rock"): 2.0,
    ("Ground", "Steel"): 2.0,

    # Flying
    ("Flying", "Electric"): 0.5,
    ("Flying", "Grass"): 2.0,
    ("Flying", "Fighting"): 2.0,
    ("Flying", "Bug"): 2.0,
    ("Flying", "Rock"): 0.5,
    ("Flying", "Steel"): 0.5,

    # Psychic
    ("Psychic", "Fighting"): 2.0,
    ("Psychic", "Poison"): 2.0,
    ("Psychic", "Psychic"): 0.5,
    ("Psychic", "Dark"): 0.0,
    ("Psychic", "Steel"): 0.5,

    # Bug
    ("Bug", "Fire"): 0.5,
    ("Bug", "Grass"): 2.0,
    ("Bug", "Fighting"): 0.5,
    ("Bug", "Poison"): 0.5,
    ("Bug", "Flying"): 0.5,
    ("Bug", "Psychic"): 2.0,
    ("Bug", "Ghost"): 0.5,
    ("Bug", "Dark"): 2.0,
    ("Bug", "Steel"): 0.5,
    ("Bug", "Fairy"): 0.5,

    # Rock
    ("Rock", "Fire"): 2.0,
    ("Rock", "Ice"): 2.0,
    ("Rock", "Fighting"): 0.5,
    ("Rock", "Ground"): 0.5,
    ("Rock", "Flying"): 2.0,
    ("Rock", "Bug"): 2.0,
    ("Rock", "Steel"): 0.5,

    # Ghost
    ("Ghost", "Normal"): 0.0,
    ("Ghost", "Psychic"): 2.0,
    ("Ghost", "Ghost"): 2.0,
    ("Ghost", "Dark"): 0.5,

    # Dragon
    ("Dragon", "Dragon"): 2.0,
    ("Dragon", "Steel"): 0.5,
    ("Dragon", "Fairy"): 0.0,

    # Dark
    ("Dark", "Fighting"): 0.5,
    ("Dark", "Psychic"): 2.0,
    ("Dark", "Ghost"): 2.0,
    ("Dark", "Dark"): 0.5,
    ("Dark", "Fairy"): 0.5,

    # Steel
    ("Steel", "Fire"): 0.5,
    ("Steel", "Water"): 0.5,
    ("Steel", "Electric"): 0.5,
    ("Steel", "Ice"): 2.0,
    ("Steel", "Rock"): 2.0,
    ("Steel", "Steel"): 0.5,
    ("Steel", "Fairy"): 2.0,

    # Fairy
    ("Fairy", "Fire"): 0.5,
    ("Fairy", "Fighting"): 2.0,
    ("Fairy", "Poison"): 0.5,
    ("Fairy", "Dragon"): 2.0,
    ("Fairy", "Dark"): 2.0,
    ("Fairy", "Steel"): 0.5,
}

# returns json dataset
def import_dataset(filename):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"//// ERROR: Unable to ingest data from [{filename}]")
        print(e)
        sys.exit(1)

# select an index at random, and return the dataset index
def rand_select(dataset):
    index = random.randint(0, len(dataset) - 1)
    item = dataset[index]
    return item

# takes reference datastruct and applies 4x moves
def assign_moves(pokemon_ds):
    movetype = pokemon_ds["type"].split("/")
    pokemon_ds["moves"] = []  # clear existing moves
    
    for i in range(4):
        sorted_moves = [move for move in ds_allmoves if move["type"] in movetype]
        rand_sortmove = random.choice(sorted_moves) if sorted_moves else None
        pokemon_ds["moves"].append(rand_sortmove)
    
    return pokemon_ds

# splice two string arrays together, return as single array of concat strings
def splicearray(firstarray, secondarray):
    newarray = []
    for i in range(len(firstarray)):
        item        = firstarray[i]
        subitem     = secondarray[i]
        newitemm    = item + subitem
        newarray.append(newitem)
    
    return newarray

def selection_menu(usrpokemon_ds):
    finalarray = []
    form = []
    for item in range(len(usrpokemon_ds)):
        form.append('|')
    
    print(splicearray(form, usrpokemon_ds))

def format_string(text: str, length: int) -> str:
    text = str(text)

    if len(text) > length:
        return text[:length]  # cut if too long
    return text + " " * (length - len(text))  # pad with spaces if too short

# return foreground colored text
def print_rgb(r, g, b, text):
    color_code = f"\033[38;2;{r};{g};{b}m"   
   
    if isinstance(text, list): # if array, iterate through and apply coloring to each
        for index, value in enumerate(text):
            text[index] = f"{color_code}{text}\033[0m"
        return text
        
    elif isinstance(text, str):
        return f"{color_code}{text}\033[0m"

# basic formatted list of pokemon loadout
def basic_pokemonshow(pokemon_ds):
    for index in pokemon_ds:
        print('─' * 58)
        banner = format_string(f"| {format_string(index["name"],12)} {format_string(f"Health:{index["health"]}",10)} {format_string(f"Defence:{index["defence"]}",10)} {format_string(f"Type:{index["type"]}",20)}",57)
        print(f"{banner}|")
        for subindex in index["moves"]:
            
            mvname = f"{format_string(subindex["name"],20)}"
            res = format_string(f"| - {mvname}    {format_string(f"pp:{subindex["pp"]}",5)} {format_string(f"pwr:{subindex["power"]}",7)} {format_string(f"acc:{subindex["accuracy"]}",6)}" , 57)
            print(f"{res}|")
        print('─' * 58)

# takes both bot and user ds, splice by side
def both_pokemonshow(pokemon_ds1, pokemon_ds2):
    array1 = []
    for index in pokemon_ds1:
        array1.append('─' * 58)
        banner = format_string(f"| {format_string(index["name"],12)} {format_string(f"Health:{index["health"]}",10)} {format_string(f"Defence:{index["defence"]}",10)} {format_string(f"Type:{index["type"]}",20)}",57)
        array1.append(f"{banner}|")
        for subindex in index["moves"]:
            
            mvname = f"{format_string(subindex["name"],20)}"
            res = format_string(f"| - {mvname}    {format_string(f"pp:{subindex["pp"]}",5)} {format_string(f"pwr:{subindex["power"]}",7)} {format_string(f"acc:{subindex["accuracy"]}",6)}" , 57)
            array1.append(f"{res}|")
        array1.append('─' * 58)

    array2 = []
    for index in pokemon_ds2:
        array2.append('─' * 58)
        banner = format_string(f"| {format_string(index["name"],12)} {format_string(f"Health:{index["health"]}",10)} {format_string(f"Defence:{index["defence"]}",10)} {format_string(f"Type:{index["type"]}",20)}",57)
        array2.append(f"{banner}|")
        for subindex in index["moves"]:
            
            mvname = f"{format_string(subindex["name"],20)}"
            res = format_string(f"| - {mvname}    {format_string(f"pp:{subindex["pp"]}",5)} {format_string(f"pwr:{subindex["power"]}",7)} {format_string(f"acc:{subindex["accuracy"]}",6)}" , 57)
            array2.append(f"{res}|")
        array2.append('─' * 58)

    returnarray = arraysplice(array1, array2)
    arrayprint(returnarray)

# old ANSI version, to be fixed
def moveselection_interface_ansi(move_ds,option):
    
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
    for index in move_ds:
        line = []
        
        #print(print_rgb(250,0,0,"UP"))

        line.append('─' * 26)
        line.append(f"| {format_string(index["name"],23)}|")
        line.append(f"| {format_string(index["type"],12)} pp: {format_string(index["pp"],6)}|")
        line.append(f"| pwr: {format_string(index["power"],7)} acc: {format_string(index["accuracy"],5)}|")
        line.append('─' * 26)

        structured_array.append(line)

    print("Press Selection ←→↑↓ ")
    arrayprint(arraysplice(structured_array[0],structured_array[1]))
    arrayprint(arraysplice(structured_array[2],structured_array[3]))
    key = get_key()

    while True:

        if key == 'A':
            arrayprint(arraysplice(structured_array[0],structured_array[1]))
            arrayprint(arraysplice(structured_array[2],structured_array[3]))
        elif key == 'B':
            arrayprint(arraysplice(structured_array[0],structured_array[1]))
            arrayprint(arraysplice(structured_array[2],structured_array[3]))
        elif key == 'C':
            arrayprint(arraysplice(structured_array[0],structured_array[1]))
            arrayprint(arraysplice(structured_array[2],structured_array[3]))
        elif key == 'D':
            arrayprint(arraysplice(structured_array[0],structured_array[1]))
            arrayprint(arraysplice(structured_array[2],structured_array[3]))
        elif key == 'q':
            break

        key = get_key()
        print("\x1b[10A", end="")

# shit version
def moveselection_interface(move_ds):
    while True:
        structured_array = []
        count = 1
        for index in move_ds:
            line = []
            
            line.append('─' * 26)
            line.append(f"| {format_string(index["name"],20)} {count} |")
            line.append(f"| {format_string(index["type"],12)} pp: {format_string(index["pp"],6)}|")
            line.append(f"| pwr: {format_string(index["power"],7)} acc: {format_string(index["accuracy"],5)}|")
            line.append('─' * 26)

            structured_array.append(line)
            count += 1

        arrayprint(arraysplice(structured_array[0],structured_array[1]))
        arrayprint(arraysplice(structured_array[2],structured_array[3]))
        
        opt = int(input("option: "))
        if opt in range(1, len(move_ds)):
            return move_ds[opt -1] # array index
        else:
            print("Error not in range")

# receives 2 arrays, concatenates by each index (ref array 1 len()) and returns third
def arraysplice(array1, array2):
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

# duel mechanism and subfunctions
# - usermode and botmode take strings "random", "user" or "ai" depending on feature
def battle(p1, p2, usermode, botmode, userds_pokemon, botds_pokemon):

    p1["max_health"] = p1["health"]
    p2["max_health"] = p2["health"]

    def calculate_damage(attacker, defender, move):
        level = 50

        if move["category"] == "Special":
            attack_stat = attacker["spc_attack"]
            defence_stat = defender["spc_defence"]
        else:
            attack_stat = attacker["spc_attack"]
            defence_stat = defender["defence"]

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
        effectiveness = type_effectiveness(
            move["type"],
            defender["type"]
        )

        # Critical hit
        critical = 1.5 if random.random() < 0.0625 else 1.0

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

    def move_hits(move):
        return random.randint(1, 100) <= move["accuracy"]

    def type_effectiveness(move_type, defender_type):
        return TYPE_EFFECTIVENESS.get(
            (move_type, defender_type),
            1.0
        )

    def apply_secondary_effect(defender, move):
        effect = move.get("effect")

        if not effect:
            return

        chance = effect.get("chance", 0)

        if random.randint(1, 100) <= chance:
            if effect.get("status") == "paralysis":
                defender.status = "paralysis"

    def use_move(attacker, defender, move):
        print(f"{attacker["name"]} used {move["name"]}!")

        if not move_hits(move):
            print("But it missed!")
            return

        damage, effectiveness, critical = calculate_damage(
            attacker,
            defender,
            move
        )

        defender["health"] -= damage
        defender["health"] = max(0, defender["health"])

        print(f"It dealt {damage} damage!")

        if critical:
            print("A critical hit!")

        if effectiveness > 1:
            print("It's super effective!")

        elif effectiveness < 1 and effectiveness > 0:
            print("It's not very effective...")

        elif effectiveness == 0:
            print("It had no effect!")

        apply_secondary_effect(defender, move)

        if defender["health"] <= 0:
            print(f"{defender["name"]} fainted!")

    def determine_order(p1, move1, p2, move2):

        if move1["priority"] > move2["priority"]:
            return [(p1, move1), (p2, move2)]

        if move2["priority"] > move1["priority"]:
            return [(p2, move2), (p1, move1)]

        if p1["speed"] > p2["speed"]:
            return [(p1, move1), (p2, move2)]

        if p2["speed"] > p1["speed"]:
            return [(p2, move2), (p1, move1)]

        if random.random() < 0.5:
            return [(p1, move1), (p2, move2)]

        return [(p2, move2), (p1, move1)]

    def interface_pkmnlist(cur_pkmn,ds_pokemon):
        pkmncount = sum(item["health"] <= 0 for item in ds_pokemon)        
        pkmnlen = len(ds_pokemon)
        left = pkmnlen - pkmncount
        form = "o" * left
        form += "x" * pkmncount
        form += f" {cur_pkmn["name"]}"

        return form

    def interface_healthbar(botds):
        bot_hpercent = (botds["health"] / botds["max_health"]) * 100
        bot_hblocks = int(round(bot_hpercent / 5))  # 100% / 20 blocks = 5% per block

        bot_hblocks = max(0, min(20, bot_hblocks))  # keep value between 0 and 20

        form = f"{botds["health"]}/{botds["max_health"]} [" + ("■" * bot_hblocks + " " * (20 - bot_hblocks)) + "]"

        return form

    def interface(p1, p2, userds_pokemon, botds_pokemon, size): # size integer to determine size of interface
        print("")
        if size == 1:
            length = 80
            print('/' * length)
            statusbar1 = interface_pkmnlist(p1,userds_pokemon)
            statusbar2 = interface_pkmnlist(p2,botds_pokemon)
            statusbar = f"{statusbar1}"
            statusbar += ' ' * (length - (len(statusbar1) + len(statusbar2)))
            statusbar += f"{statusbar2}"
            print(statusbar)

            bar1 = interface_healthbar(p1)
            bar2 = interface_healthbar(p2)
            healthbar = f"{bar1}"
            healthbar += ' ' * (length - (len(bar1) + len(bar2)))
            healthbar += f"{bar2}"
            print(healthbar)
            print("")

    while p1["health"] > 0 and p2["health"] > 0:
        user_pkmncount = sum(item["health"] > 0 for item in userds_pokemon)
        bot_pkmncount = sum(item["health"] > 0 for item in botds_pokemon)


        interface(p1,p2,userds_pokemon,botds_pokemon,1)
        if usermode == "random":
            move1 = random.choice(p1["moves"])
        elif usermode == "user":
            move1 = moveselection_interface(p1["moves"])
        elif usermode == "ai":
            print("")
            # function coming soon

        if botmode == "random":
            move2 = random.choice(p2["moves"])
        elif botmode == "user":
            move2 = moveselection_interface(p2["moves"])
        elif botmode == "ai":
            print("")
            # function coming soon

        order = determine_order(
            p1, move1,
            p2, move2
        )

        first_pokemon, first_move = order[0]
        second_pokemon, second_move = order[1]

        target = p2 if first_pokemon == p1 else p1

        use_move(
            first_pokemon,
            target,
            first_move
        )

        if target["health"] <= 0:
            break

        target = p2 if second_pokemon == p1 else p1

        use_move(
            second_pokemon,
            target,
            second_move
        )

        print(
            f"{p1["name"]}: {p1["health"]}/{p1["max_health"]} HP"
        )
        print(
            f"{p2["name"]}: {p2["health"]}/{p2["max_health"]} HP"
        )

    if p1["health"] <= 0:
        print(f"{p2["name"]} wins!\n")
        return p1, p2
    elif p2["health"] <= 0:
        print(f"{p1["name"]} wins!\n")
        return p1, p2





ds_allpokemon   = import_dataset("pokemon_datafile.json")
ds_allmoves     = import_dataset("moves_datafile.json")

print(f"Ingested [{len(ds_allpokemon)}] into Pokemon dataset")
print(f"Ingested [{len(ds_allmoves)}] into Moves dataset")

print("Select gamemode:")
print(" -[1]- random")
print(" -[2]- select pokemon")

opt = input("\nSelection: ")
if opt == '1':
    print("\n   Randomly selected:")
    count = 0
    while count < 4: # randomly select 4 pokemon for user
        userds_pokemon.append(rand_select(ds_allpokemon))
        userds_pokemon[count] = assign_moves(userds_pokemon[count])
        count = count + 1

elif opt == '2':
    print("")
    counter = 0
    for item in ds_allpokemon: # list pokemon
        print(f"-[{counter}]- {item["name"]}")
        time.sleep(0.01)
        counter += 1

    selection = input("Select 4x pokemon numbers: ")

    div = selection.split(" ")
    for item in div : # bind integers to 
        matchname = ds_allpokemon[int(item)] # match int(str) selection to array
        for pokemon in ds_allpokemon:
            if pokemon["name"] == matchname["name"]: # append selection to userds_pokemon if name match
                userds_pokemon.append(pokemon)
                userds_pokemon[-1] = assign_moves(userds_pokemon[-1])

else :
    print("ERROR: Unrecognised input")


#for i in userds_pokemon:
#    print(f"{i["name"]} movelen {len(i["moves"])}")

# randomly select 4 pokemon for ai
for i in range(4): # randomly select 4 pokemon
    botds_pokemon.append(rand_select(ds_allpokemon))
    botds_pokemon[-1] = assign_moves(botds_pokemon[-1])

print("")
print("BOT and User Selected Pokemon:")

both_pokemonshow(userds_pokemon, botds_pokemon)

print("----------------------------------------------------------------------")

# Primary battle loop protocol
counter = 1 # while all userds_pokemon["health"] > 0 and same for botds
while (any(item["health"] > 0 for item in userds_pokemon)) and (any(item["health"] > 0 for item in botds_pokemon)):
    print(f"ROUND [{counter}]")
    for user_pokemon in userds_pokemon :
        if user_pokemon["health"] > 0 :
            break
    for bot_pokemon in botds_pokemon :
        if bot_pokemon["health"] > 0 :
            break
    user_pokemon, bot_pokemon = battle(user_pokemon,bot_pokemon, "random","random",userds_pokemon,botds_pokemon)
    counter += 1

if (all(item["health"] <= 0 for item in userds_pokemon)):
    print("BOT WINS")
elif (all(item["health"] <= 0 for item in botds_pokemon)):
    print("PLAYER WINS")

