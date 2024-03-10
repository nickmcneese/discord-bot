import discord
import pymongo
import re
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord import Client, Intents
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()
uri = os.getenv("MONGO_URI")

client = MongoClient(uri, server_api=ServerApi('1'))

db = client["Users"]
currency_collection = db["currency"]
ranking_collection = db["ranking"]


BOT_TOKEN = os.getenv("BOT_TOKEN")
MAX_USER_DAILY_RANKING_CURRENCY = 50

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_guild_join(guild):
    print(f"Added to {guild.name}. Adding all members to the databases...")
    for member in guild.members:
        if member.name != "rating-bot":
            ranking_data = {
                "member": member.name,
                "ranking": 0,
                "ranking_delta": 0
            }
            currency_data = {
                "author": member.name,
                "amount_positive": MAX_USER_DAILY_RANKING_CURRENCY,
                "amount_negative": MAX_USER_DAILY_RANKING_CURRENCY
            }
            ranking_collection.insert_one(ranking_data)
            currency_collection.insert_one(currency_data)

    print(f"Added all members of {guild.name} to the databases.")

#want to add new discord server members to both databases
@bot.event
async def on_member_join(member):
    #join rank DB
    member = member.name
    ranking_document = ranking_collection.find_one({"member": member})
    if ranking_document:
        print(f"The person already exists in the ranking document.")
    else:
        print(f"The person does not exist in the ranking document. Inserting...")
        data = {
            "member": member,
            "ranking": 0,
            "ranking_delta": 0,
        }
        ranking_collection.insert_one(data)
    
    #join currency DB
    currency_document = currency_collection.find_one({"author": member})
    if currency_document:
        print(f"The person already exists in the document!")
    else:
        print(f"The person does not exist in the document. Inserting...")
        data = {
            "author": member,
            "amount_positive": MAX_USER_DAILY_RANKING_CURRENCY,
            "amount_negative": MAX_USER_DAILY_RANKING_CURRENCY,
        }
        currency_collection.insert_one(data)

def find_member(guild, username):
    # Search for the member by username or user ID
    member = discord.utils.find(
        lambda m: username.lower() in m.name.lower() or str(m.id) == username,
        guild.members
    )
    return member

@bot.command()
async def rating(ctx, username):
    member = find_member(ctx.guild, username).name
    ranking_document = ranking_collection.find_one({"member": member})
    delta = ranking_document["ranking_delta"]
    if ranking_document:
        rank_emoji = None
        if delta == 1:
            rank_emoji = ":chart_with_upwards_trend:"
        else:
            rank_emoji = ":chart_with_downwards_trend:"
        await ctx.send("Current rating: " + str(ranking_document["ranking"]) + " " + rank_emoji)
    else:
        await ctx.send("Error. This person is not in the server.")
    
def parse_input(input_string):
    pattern = r'^\d+$'

    if re.match(pattern, input_string):
        # Valid format
        number = int(input_string)
        return number
    else:
        # Invalid format
        return "Error"

@bot.command()
async def buy(ctx, username, input):
    #caller of command by unique discord username
    author = ctx.author.name

    #parse input
    result = parse_input(input)
    if result == "Error":
        await ctx.send("Error, wrong format!")
        return
    integer = result

    #check if user exists
    member = find_member(ctx.guild, username).name

    #make sure you can't rate yourself
    if member == author:
        await ctx.send("You cannot give rating to yourself!")
        return

    #check if author is in the currency table. if they are not, add them.
    currency_document = currency_collection.find_one({"author": author})
    if currency_document:
        print(f"The person already exists in the document.")
    else:
        print(f"The person does not exist in the document. Inserting...")
        data = {
            "author": author,
            "amount_positive": MAX_USER_DAILY_RANKING_CURRENCY,
            "amount_negative": MAX_USER_DAILY_RANKING_CURRENCY,
        }
        currency_collection.insert_one(data)
    
    #Check if user exceeds their daily limit. If so, give error. Else, subtract.
    entry = currency_collection.find_one({"author": author})
    amount_positive = entry["amount_positive"]
    amount_negative = entry["amount_negative"]
    if amount_positive - integer >= 0:
        new_value = {"$set": {"amount_positive" : amount_positive - integer}}
        currency_collection.update_one(entry, new_value)
    else:
        await ctx.send("Not enough daily currency! Buy amount remaining: " + str(amount_positive) + ". Sell amount remaining: " + str(amount_negative) + ".")
        return

    #Update ranking for the member specified based on amount
    #First have to check if member is in the ranking DB, otherwise add them
    ranking_document = ranking_collection.find_one({"member": member})
    if ranking_document:
        print(f"The person already exists in the ranking document.")
    else:
        print(f"The person does not exist in the ranking document. Inserting...")
        data = {
            "member": member,
            "ranking": 0,
            "ranking_delta": 0
        }
        ranking_collection.insert_one(data)
    
    #Now we update their ranking
    entry = ranking_collection.find_one({"member": member})
    current_ranking = entry["ranking"]
    rank_emoji = None
    new_value = {"$set": { "ranking": current_ranking + integer, "ranking_delta": 1 }}
    ranking_collection.update_one(entry, new_value)
    rank_emoji = ":chart_with_upwards_trend:"

    new_rank = ranking_collection.find_one({"member": member})["ranking"]
    await ctx.send("Updated rating for " + username + "! New rating is: " + str(new_rank) + " " + rank_emoji)

@bot.command()
async def sell(ctx, username, input):
    #caller of command by unique discord username
    author = ctx.author.name

    #parse input
    result = parse_input(input)
    if result == "Error":
        await ctx.send("Error, wrong format!")
        return
    integer = result

    #check if user exists
    member = find_member(ctx.guild, username).name

    #make sure you can't rate yourself
    if member == author:
        await ctx.send("You cannot give rating to yourself!")
        return

    #check if author is in the currency table. if they are not, add them.
    currency_document = currency_collection.find_one({"author": author})
    if currency_document:
        print(f"The person already exists in the document.")
    else:
        print(f"The person does not exist in the document. Inserting...")
        data = {
            "author": author,
            "amount_positive": MAX_USER_DAILY_RANKING_CURRENCY,
            "amount_negative": MAX_USER_DAILY_RANKING_CURRENCY,
        }
        currency_collection.insert_one(data)
    
    #Check if user exceeds their daily limit. If so, give error. Else, subtract.
    entry = currency_collection.find_one({"author": author})
    amount_positive = entry["amount_positive"]
    amount_negative = entry["amount_negative"]
    if amount_negative - integer >= 0:
        new_value = {"$set": {"amount_negative" : amount_negative - integer}}
        currency_collection.update_one(entry, new_value)
    else:
        await ctx.send("Not enough daily currency! Buy amount remaining: " + str(amount_positive) + ". Sell amount remaining: " + str(amount_negative) + ".")
        return

    #Update ranking for the member specified based on amount
    #First have to check if member is in the ranking DB, otherwise add them
    ranking_document = ranking_collection.find_one({"member": member})
    if ranking_document:
        print(f"The person already exists in the ranking document.")
    else:
        print(f"The person does not exist in the ranking document. Inserting...")
        data = {
            "member": member,
            "ranking": 0,
            "ranking_delta": 0
        }
        ranking_collection.insert_one(data)
    
    #Now we update their ranking
    entry = ranking_collection.find_one({"member": member})
    current_ranking = entry["ranking"]
    rank_emoji = None
    new_value = {"$set": { "ranking": current_ranking - integer, "ranking_delta": -1 }}
    ranking_collection.update_one(entry, new_value)
    rank_emoji = ":chart_with_downwards_trend:"

    new_rank = ranking_collection.find_one({"member": member})["ranking"]
    await ctx.send("Updated rating for " + username + "! New rating is: " + str(new_rank) + " " + rank_emoji)


@buy.error
async def buy_error(ctx, error):
    if isinstance(error, commands.errors.UserNotFound):
        await ctx.send("User not on server")

@sell.error
async def sell_error(ctx, error):
    if isinstance(error, commands.errors.UserNotFound):
        await ctx.send("User not on server")

@bot.command()
async def currency(ctx):
    author = ctx.author.name
    currency_document = currency_collection.find_one({"author": author})
    if currency_document:
        amount_positive = currency_document["amount_positive"]
        amount_negative = currency_document["amount_negative"]
        await ctx.send("You have " + str(amount_positive) + " buying power and " + str(amount_negative) + " selling power left to spend for today!")
        return
    else:
        await ctx.send("You are not yet in the system.")
        return
 
bot.run(BOT_TOKEN)