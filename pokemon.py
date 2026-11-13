import argparse
import copy
import json
import sys
import time
import random
import uuid
from battle_procedure import (
    BattleProcedure,
    format_string,
)

ds_allmoves         = []
ds_allpokemon       = []
userds_pokemon      = [] # includes moves
botds_pokemon       = []
actionlog           = [] # complete list of things that happened, and both pkmn states

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

# clone a dataset template into an independent battle instance with a
# unique primary key, so teams never share mutable state by reference
def new_pokemon(template):
    pokemon_ds = copy.deepcopy(template)
    pokemon_ds["id"] = uuid.uuid4().hex
    pokemon_ds["max_health"] = pokemon_ds["health"]
    pokemon_ds["status"] = []
    pokemon_ds["volatile"] = {}
    pokemon_ds["stat_stages"] = {}
    pokemon_ds["status_turns"] = {}
    return assign_moves(pokemon_ds)

# splice two string arrays together, return as single array of concat strings
def splicearray(firstarray, secondarray):
    newarray = []
    for i in range(len(firstarray)):
        item        = firstarray[i]
        subitem     = secondarray[i]
        newitem     = item + subitem
        newarray.append(newitem)
    
    return newarray

def selection_menu(usrpokemon_ds):
    finalarray = []
    form = []
    for item in range(len(usrpokemon_ds)):
        form.append('|')
    
    print(arraysplice(form, usrpokemon_ds))

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

def sys1_access(query):
    print()


# optional launch parameters: python pokemon.py [-p POKEMON_SELECTION] [-u USER_MOVES] [-b BOT_MOVES]
# anything not supplied at launch defers to the interactive user input below
parser = argparse.ArgumentParser(description="Pokemon battle launcher")
parser.add_argument("-p", "--pokemon-selection", dest="pokemon_selection", default=None,
    help='"random" or indices e.g. "0,4,7,25" / "0 4 7 25" (prompts if omitted)',
)

parser.add_argument("-u", "--user-moves", dest="user_moves", default=None, choices=["random", "ai", "user"],
    help="user move logic (prompts if omitted)",
)

parser.add_argument("-b", "--bot-moves", dest="bot_moves", default=None, choices=["random", "ai"],
    help="bot move logic (prompts if omitted)",
)

args = parser.parse_args()

launch_pokemon_selection = args.pokemon_selection
launch_user_moves        = args.user_moves
launch_bot_moves         = args.bot_moves

ds_allpokemon   = import_dataset("pokemon_datafile.json")
ds_allmoves     = import_dataset("moves_datafile.json")

print(f"Ingested [{len(ds_allpokemon)}] into Pokemon dataset")
print(f"Ingested [{len(ds_allmoves)}] into Moves dataset")

if launch_pokemon_selection is None:
    print("\npkmn Selection Logic:")
    print(" -[1]- random")
    print(" -[2]- select pokemon")
    opt = input("Selection: ")
elif launch_pokemon_selection == "random":
    opt = '1'
else:
    opt = '2'

if opt == '1':
    for i in range(4): # randomly select 4 pokemon for user
        userds_pokemon.append(new_pokemon(rand_select(ds_allpokemon)))

elif opt == '2':
    if launch_pokemon_selection is None:
        print("")
        counter = 0
        for item in ds_allpokemon: # list pokemon
            print(f"-[{counter}]- {item["name"]}")
            time.sleep(0.01)
            counter += 1

        selection = input("Select 4x pokemon numbers: ")
    else:
        selection = launch_pokemon_selection.replace(",", " ")

    div = selection.split(" ")
    for item in div : # bind integers to 
        matchname = ds_allpokemon[int(item)] # match int(str) selection to array
        userds_pokemon.append(new_pokemon(matchname))

else :
    print("ERROR: Unrecognised input")
    sys.exit()

if launch_user_moves is None:
    print("\nUser move selection Logic:")
    print(" -[1]- random")
    print(" -[2]- ai")
    print(" -[3]- user")
    opt = input("Selection: ")

    if opt == '1': 
        USER_MOVETYPE = "random"
    elif opt == '2':
        USER_MOVETYPE = "ai"
    elif opt == '3': 
        USER_MOVETYPE = "user"
    else:
        print(" - ERROR: Unrecognised input")
        sys.exit()
else:
    USER_MOVETYPE = launch_user_moves

if launch_bot_moves is None:
    print("\nBOT move selection Logic:")
    print(" -[1]- random")
    print(" -[2]- ai")
    opt = input("Selection: ")

    if opt == '1': 
        BOT_MOVETYPE = "random"
    elif opt == '2': 
        BOT_MOVETYPE = "ai"
    else:
        print(" - ERROR: Unrecognised input")
        sys.exit()
else:
    BOT_MOVETYPE = launch_bot_moves

#for i in userds_pokemon:
#    print(f"{i["name"]} movelen {len(i["moves"])}")

# randomly select 4 pokemon for ai
for i in range(4): # randomly select 4 pokemon
    botds_pokemon.append(new_pokemon(rand_select(ds_allpokemon)))

#print(json.dumps(userds_pokemon[0], indent=4))

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
    procedure = BattleProcedure(
        user_pokemon,
        bot_pokemon,
        USER_MOVETYPE,
        BOT_MOVETYPE,
        userds_pokemon,
        botds_pokemon,
        actionlog,
    )
    result = procedure.run_round()
    user_pokemon = result["p1"]
    bot_pokemon = result["p2"]

    counter += 1

if (all(item["health"] <= 0 for item in userds_pokemon)):
    print("BOT WINS")
elif (all(item["health"] <= 0 for item in botds_pokemon)):
    print("PLAYER WINS")

