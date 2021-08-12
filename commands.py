'''
Created on Jun 26, 2021

@author: willg
'''

#Bot internal imports - stuff I coded
import WiimfiSiteFunctions
from WiimfiSiteFunctions import _is_rLID, _is_fc
import ServerFunctions
import ImageCombine
import War
from TagAI import getTagsSmart, getTagSmart
import LoungeAPIFunctions
import ScoreKeeper as SK
import UserDataProcessing
from UserDataProcessing import lounge_add
import TableBot
from TableBot import ChannelBot
import UtilityFunctions
import MiiPuller
import SimpleRooms
import Race
import MogiUpdate
import Lounge
import TableBotExceptions
import AbuseTracking
import common



#Other library imports, other people codes
from typing import List, Set
import asyncio
from collections.abc import Callable
import urllib
import copy
import dill as pkl
import subprocess
import gc
from builtins import staticmethod
import itertools
import discord
import os
from datetime import datetime
import URLShortener

vr_is_on = False



async def sendRoomWarNotLoaded(message: discord.Message, serverPrefix:str, is_lounge=False):
    if is_lounge:
        return await message.channel.send(f"Room is not loaded! Use the command `{serverPrefix}sw mogiformat numberOfTeams` to load a room.")  
    else:
        return await message.channel.send(f"Room is not loaded! Use the command `{serverPrefix}sw warformat numberOfTeams (LoungeName/rxx/FC) (gps=numberOfGPs) (psb=on/off) (miis=yes/no)` to start a war.")  

async def updateData(id_lounge, fc_id):
    UserDataProcessing.smartUpdate(id_lounge, fc_id)
    
async def send_missing_permissions(channel:discord.TextChannel, content=None, delete_after=7):
    try:
        return await channel.send("I'm missing permissions. Contact your admins. The bot needs these additional permissions:\n- Send Messages\n- Add Reactions (for pages)\n- Manage Messages (to remove reactions)", delete_after=delete_after)
    except discord.errors.Forbidden: #We can't send messages
        pass
    
        
            
        
"""============== Bad Wolf only commands ================"""
#TODO: Refactor these - target the waterfall-like if-statements
class BadWolfCommands:
    """There is no point to this class, other than for organization purposes.
    This class contains all of the commands that are private and only available to me"""
    
    @staticmethod
    def is_badwolf_check(author, failure_message):
        if not common.is_bad_wolf(author):
            raise TableBotExceptions.NotBadWolf(failure_message)
        return True
    
    @staticmethod
    async def get_logs_command(message:discord.Message):
        BadWolfCommands.is_badwolf_check(message.author, "cannot give logs")
        
        if os.path.exists(common.FEEDBACK_LOGS_FILE):
            await message.channel.send(file=discord.File(common.FEEDBACK_LOGS_FILE))
        if os.path.exists(common.ERROR_LOGS_FILE):
            await message.channel.send(file=discord.File(common.ERROR_LOGS_FILE))
        if os.path.exists(common.MESSAGE_LOGGING_FILE):
            await message.channel.send(file=discord.File(common.MESSAGE_LOGGING_FILE))
        if os.path.exists(common.FULL_MESSAGE_LOGGING_FILE):
            await message.channel.send(file=discord.File(common.FULL_MESSAGE_LOGGING_FILE))

        
    #Adds or removes a discord ID to/from the bot admins
    @staticmethod
    async def bot_admin_change(message:discord.Message, args:List[str], adding=True):
        if len(args) <= 1:
            await message.channel.send("Give a Discord ID.")
            return
        
        admin_id = str(args[1].strip())
        
        success = UtilityFunctions.addBotAdmin(admin_id) if adding else UtilityFunctions.removeBotAdmin(admin_id)
        if success:
            add_or_remove = "Added" if adding else "Removed"
            await message.channel.send(f"{add_or_remove} discord ID {admin_id} as a bot admin.")
        else:
            await message.channel.send("Something went wrong. Try again.")
    
    
    @staticmethod
    async def add_bot_admin_command(message:discord.Message, args:List[str]):
        BadWolfCommands.is_badwolf_check(message.author, "cannot add bot admin")
        await BadWolfCommands.bot_admin_change(message, args, adding=True)
        
    @staticmethod
    async def remove_bot_admin_command(message:discord.Message, args:List[str]):
        BadWolfCommands.is_badwolf_check(message.author, "cannot remove bot admin")
        await BadWolfCommands.bot_admin_change(message, args, adding=False)
    
    @staticmethod
    async def server_process_memory_command(message:discord.Message):
        BadWolfCommands.is_badwolf_check(message.author, "cannot show server memory usage")
        command_output = subprocess.check_output('top -b -o +%MEM | head -n 22', shell=True, text=True)
        await message.channel.send(command_output)
        
    @staticmethod
    async def add_fact_command(message:discord.Message, command:str, bad_wolf_facts:List[str], data_save):
        BadWolfCommands.is_badwolf_check(message.author, "cannot add fact")
        fact = " ".join(command.split()[1:]).strip()
        if len(fact) == 0:
            await message.channel.send("Cannot add empty fact.")
            return
        bad_wolf_facts.append(fact)
        data_save()
        await message.channel.send(f"Added: {fact}")
        
        
    
    @staticmethod
    async def remove_fact_command(message:discord.Message, args:List[str], bad_wolf_facts:List[str], data_save):
        BadWolfCommands.is_badwolf_check(message.author, "cannot remove fact")
        index = "".join(args[1:])
        if not index.isnumeric() or int(index) < 0 or int(index) >= len(bad_wolf_facts):
            await message.channel.send(f"Cannot remove fact at index {index}")
            return
        removed_fact = bad_wolf_facts.pop(int(index))
        data_save()
        await message.channel.send(f"Removed: {removed_fact}")
  
  
    @staticmethod
    async def garbage_collect_command(message:discord.Message):
        BadWolfCommands.is_badwolf_check(message.author, "cannot garbage collect")
        gc.collect()
        await message.channel.send("Collected")
    
    
    @staticmethod
    async def send_all_facts_command(message:discord.Message, bad_wolf_facts:List[str]):
        BadWolfCommands.is_badwolf_check(message.author, "cannot display facts")
        if len(bad_wolf_facts) > 0:
            await message.channel.send("\n".join(bad_wolf_facts))
    
    
    @staticmethod
    async def total_clear_command(message:discord.Message, lounge_update_data):
        BadWolfCommands.is_badwolf_check(message.author, "cannot clear lounge table submission cooldown tracking")
        lounge_update_data.update_cooldowns.clear()
        await message.channel.send("Cleared.")
        
    @staticmethod
    async def dump_data_command(message:discord.Message, data_dump_function):
        BadWolfCommands.is_badwolf_check(message.author, "cannot dump data")
        successful = await UserDataProcessing.dump_data()
        data_dump_function()
        if successful:
            await message.channel.send("Completed.")        
        else:
            await message.channel.send("Failed.")  
  
 
        
"""================ Bot Admin Commands =================="""
#TODO: Refactor these - target the waterfall-like if-statements
class BotAdminCommands:
    """There is no point to this class, other than for organization purposes.
    This class contains the commands that only Bot Admins can do"""
    
    @staticmethod
    def is_bot_admin_check(author, failure_message):
        if not common.is_bot_admin(author):
            raise TableBotExceptions.NotBotAdmin(failure_message)
        return True
    
    @staticmethod
    async def blacklisted_word_change(message:discord.Message, args:List[str], adding=True):
        if len(args) <= 1:
            to_send = "Give a word to blacklist." if adding else "Specify a word to remove from the blacklist."
            await message.channel.send(to_send)
            return
        word = str(args[1].strip())
        success = UtilityFunctions.add_blacklisted_word(word) if adding else UtilityFunctions.remove_blacklisted_word(word)
        if success:
            to_send = f"Blacklisted the word: {word}" if adding else f"Removed this word from the blacklist: {word}"
        else:
            await message.channel.send("Something went wrong. Try again.")
            
    @staticmethod
    async def remove_blacklisted_word_command(message:discord.Message, args:List[str]):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot remove blacklisted word")
        await BadWolfCommands.blacklisted_word_change(message, args, adding=False)
    
    @staticmethod
    async def add_blacklisted_word_command(message:discord.Message, args:List[str]):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot add blacklisted word")
        await BadWolfCommands.blacklisted_word_change(message, args, adding=True)
        
    
    @staticmethod
    async def blacklist_user_command(message:discord.Message, args:List[str], command:str):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot blacklist user")
        
        if len(args) < 2:
            await message.channel.send(f"Give a Discord ID to blacklist. If you do not specify a reason for blacklisting a user, the given discord ID will be **removed** from the blacklist. To blacklist a discord ID, give a reason. `?{args[0]} <discordID> (reason)`")
            return
        
        if len(args) == 2:
            if UserDataProcessing.add_Blacklisted_user(args[1], ""):
                await message.channel.send("Removed blacklist for " + command.split()[1])
            else:
                await message.channel.send("Blacklist failed.")
            return
    
        if UserDataProcessing.add_Blacklisted_user(args[1], " ".join(command.split()[2:])):
            await message.channel.send("Blacklisted " + args[1])
        else:
            await message.channel.send("Blacklist failed.") 
    
    @staticmethod
    async def change_flag_exception(message:discord.Message, args:List[str], user_flag_exceptions:Set[int], adding=True):
        if len(args) <= 1:
            await message.channel.send("You must give a discord ID.")
            return
        
        if not args[1].isnumeric():
            await message.channel.send("The discord ID given is not a valid number.")
            return
    
        user_exception = int(args[1])
        if adding:
            user_flag_exceptions.add(int(args[1]))
        else:
            user_flag_exceptions.discard(user_exception)
        
        UserDataProcessing.flag_exception(user_exception, adding)
            
        await message.channel.send(f"{user_exception} can {'now add flags' if adding else 'no longer add flags'}.")
    
    @staticmethod
    async def add_flag_exception_command(message:discord.Message, args:List[str], user_flag_exceptions:Set[int]):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot give user ID a flag exception privilege")
        await BadWolfCommands.change_flag_exception(message, args, user_flag_exceptions, adding=True)
    
    @staticmethod      
    async def remove_flag_exception_command(message:discord.Message, args:List[str], user_flag_exceptions:Set[int]):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot remove user ID's flag exception privilege")
        await BadWolfCommands.change_flag_exception(message, args, user_flag_exceptions, adding=False)
    
    @staticmethod
    async def change_ctgp_region_command(message:discord.Message, args:List[str]):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot change CTGP CTWW region")
        if len(args) <= 1:
            await message.channel.send("You must give a new CTGP region to use for displaying CTGP WWs.")
        else:
            Race.set_ctgp_region(args[1])
            await message.channel.send(f"CTGP WW Region set to: {args[1]}")
    
    @staticmethod
    async def global_vr_command(message:discord.Message, on=True):
        BotAdminCommands.is_bot_admin_check(message.author, "cannot change vr on/off")

        global vr_is_on
        vr_is_on = on
        dump_vr_is_on()
        await message.channel.send(f"Turned !vr/?vr {'on' if on else 'off'}.")





"""================== Other Commands ===================="""
#TODO: Refactor these - target the waterfall-like if-statements
class OtherCommands:
    """There is no point to this class, other than for organization purposes.
    This class contains all of the non administrative "stateless" commands"""
    
    @staticmethod
    async def get_flag_command(message:discord.Message, server_prefix:str):
        author_id = message.author.id
        flag = UserDataProcessing.get_flag(author_id)
        if flag is None:
            await message.channel.send(f"You don't have a flag set. Use {server_prefix}setflag [flag] to set your flag for tables. Flag codes can be found at: {common.LORENZI_FLAG_PAGE_URL_NO_PREVIEW}")
            return
        
        image_name = ""
        if flag.startswith("cl_") and flag.endswith("u"): #Remap this specific flag code to a specific picture
            image_name += 'cl_C3B1u.png'
        else:
            image_name += f"{flag}.png"
            
        embed = discord.Embed(colour = discord.Colour.dark_blue())
        file = discord.File(f"{common.FLAG_IMAGES_PATH}{image_name}", filename=image_name)
        embed.set_thumbnail(url=f"attachment://{image_name}")
        await message.channel.send(file=file, embed=embed)
        
    @staticmethod
    async def set_flag_command(message:discord.Message, args:List[str], user_flag_exceptions:Set[int]): 
        author_id = message.author.id
        if len(args) > 1:
            #if 2nd argument is numeric, it's a discord ID
            if args[1].isnumeric(): #This is an admin attempt
                if str(author_id) in common.botAdmins:
                    if len(args) == 2 or args[2] == "none":
                        UserDataProcessing.add_flag(args[1], "")
                        await message.channel.send(str(args[1] + "'s flag was successfully removed."))
                    else:
                        UserDataProcessing.add_flag(args[1], args[2].lower())
                        await message.channel.send(str(args[1] + "'s flag was successfully added and will now be displayed on tables."))
                elif author_id in user_flag_exceptions:
                    flag = UserDataProcessing.get_flag(int(args[1]))
                    if flag is None:
                        UserDataProcessing.add_flag(args[1], args[2].lower())
                        await message.channel.send(str(args[1] + "'s flag was successfully added and will now be displayed on tables."))
                    else:
                        await message.channel.send("This person already has a flag set.")
                else:
                    await message.channel.send("You are not a bot admin, nor do you have an exception for adding flags.")

            elif len(args) >= 2:
                if args[1].lower() not in UserDataProcessing.valid_flag_codes:
                    await message.channel.send(f"This is not a valid flag code. For a list of flags and their codes, please visit: {common.LORENZI_FLAG_PAGE_URL_NO_PREVIEW}")
                    return
                
                if args[1].lower() == "none":
                    UserDataProcessing.add_flag(author_id, "")
                    await message.channel.send(f"Your flag was successfully removed. If you want to add a flag again in the future, pick a flag code from this website: {common.LORENZI_FLAG_PAGE_URL_NO_PREVIEW}")
                    return

                UserDataProcessing.add_flag(author_id, args[1].lower())
                await message.channel.send("Your flag was successfully added and will now be displayed on tables.")
                return
            
        elif len(args) == 1:
            UserDataProcessing.add_flag(author_id, "")
            await message.channel.send(f"Your flag was successfully removed. If you want to add a flag again in the future, pick a flag code from this website: {common.LORENZI_FLAG_PAGE_URL_NO_PREVIEW}")


    @staticmethod
    async def log_feedback_command(message:discord.Message, args:List[str], command:str):
        if len(args) > 1:
            to_log = f"{message.author} - {message.author.id}: {command}"
            common.log_text(to_log, common.FEEDBACK_LOGGING_TYPE)
            await message.channel.send("Logged") 

    @staticmethod
    async def lounge_name_command(message:discord.Message):
        author_id = message.author.id
        discordIDToLoad = str(author_id)
        await updateData(* await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad]))
        lounge_name = UserDataProcessing.get_lounge(author_id)
        if lounge_name is None:
            await message.channel.send("You don't have a lounge name. Join Lounge! (If you think this is an error, go on Wiimmfi and try running this command again.)")
        else:
            await message.channel.send("Your lounge name is: " + UtilityFunctions.process_name(str(lounge_name)))
            

    @staticmethod
    async def fc_command(message:discord.Message, args:List[str], old_command:str):
        discordIDToLoad = None
        id_lounge = {}
        fc_id = {}
        
        if len(args) == 1:
            discordIDToLoad = str(message.author.id)
            id_lounge, fc_id = await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad])
            await updateData(id_lounge, fc_id)
        else:
            if len(message.raw_mentions) > 0:
                discordIDToLoad = str(message.raw_mentions[0])
                id_lounge, fc_id = await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad])  
            else:
                to_find_lounge = " ".join(old_command.split()[1:])
                id_lounge, fc_id = await LoungeAPIFunctions.getByLoungeNames([to_find_lounge])
                if id_lounge is not None and len(id_lounge) == 1:
                    for this_id in id_lounge:
                        discordIDToLoad = this_id
                        break
                if discordIDToLoad is None:
                    discordIDToLoad = UserDataProcessing.get_DiscordID_By_LoungeName(to_find_lounge)
                    
        await updateData(id_lounge, fc_id)    
        FC = None
        if fc_id is not None and id_lounge is not None: #This would only occur it the API went down...
            for fc, _id in fc_id.items():
                if _id == discordIDToLoad:
                    FC = fc
                    break
        if FC is None:
            FCs = UserDataProcessing.get_all_fcs(discordIDToLoad)
            if len(FCs) > 0:
                FC = FCs[0]
    
        if FC is None:
            if len(args) == 1:
                await message.channel.send("You have not set an FC. (Use Friendbot to add your FC, then try this command later.")
            elif len(message.raw_mentions) > 0:
                lookup_name = UtilityFunctions.process_name(str(message.mentions[0].name))
                await message.channel.send(f"No FC found for {lookup_name}. Try again later.")                      
            else:
                lookup_name = UtilityFunctions.process_name(" ".join(old_command.split()[1:]))
                await message.channel.send(f"No FC found for {lookup_name}. Try again later.")                      
        else:
            await message.channel.send(FC)
      
    @staticmethod
    async def mii_command(message:discord.Message, args:List[str], old_command:str):
        if common.MIIS_DISABLED:
            await message.channel.send("This command is temporarily disabled.")
            return
        
        discordIDToLoad = None
        if len(args) == 1:
            discordIDToLoad = str(message.author.id)
        else:
            if len(message.raw_mentions) > 0:
                discordIDToLoad = str(message.raw_mentions[0])
            else:
                to_find_lounge = " ".join(old_command.split()[1:])
                discordIDToLoad = UserDataProcessing.get_DiscordID_By_LoungeName(to_find_lounge)
                if discordIDToLoad is None or discordIDToLoad == "":
                    discordIDToLoad = to_find_lounge
    
    
        FC = None
        if _is_fc(discordIDToLoad):
            FC = discordIDToLoad
        else:
            id_lounge, fc_id = await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad])
            await updateData(id_lounge, fc_id)
            FCs = UserDataProcessing.get_all_fcs(discordIDToLoad)
            if len(FCs) > 0:
                FC = FCs[0]
            
        if FC is None:
            if len(args) == 1:
                await message.channel.send("You have not set an FC. (Use Friendbot to add your FC, then try this command later.")
            elif len(message.raw_mentions) > 0:
                lookup_name = UtilityFunctions.process_name(str(message.mentions[0].name))
                await message.channel.send(f"No FC found for {lookup_name}, so cannot find the mii. Try again later.")                      
            else:
                lookup_name = UtilityFunctions.process_name(' '.join(old_command.split()[1:]))
                await message.channel.send(f"No FC found for {lookup_name}, so cannot find the mii. Try again later.")                      
        else:
            mii = await MiiPuller.get_mii(FC, str(message.id))
            if isinstance(mii, str):
                await message.channel.send(mii)
            else:
                try:
                    file, embed = mii.get_mii_embed()
                    await message.channel.send(file=file, embed=embed)
                finally:
                    mii.clean_up()
                    
    @staticmethod
    async def wws_command(client, this_bot:TableBot.ChannelBot, message:discord.Message, ww_type=Race.RT_WW_ROOM_TYPE):
        rlCooldown = this_bot.getRLCooldownSeconds()
        if rlCooldown > 0:
            delete_me = await message.channel.send(f"Wait {rlCooldown} more seconds before using this command.")
            await delete_me.delete(delay=5)
        else:
            
            this_bot.updateRLCoolDown()
            sr = SimpleRooms.SimpleRooms()
            await sr.populate_rooms_information()
            rooms = []
            if ww_type == Race.RT_WW_ROOM_TYPE:
                rooms = sr.get_RT_WWs()
            elif ww_type == Race.CTGP_CTWW_ROOM_TYPE:
                rooms = sr.get_CTGP_WWs()
            elif ww_type == Race.BATTLE_ROOM_TYPE:
                rooms = sr.get_battle_WWs()
            elif ww_type == Race.UNKNOWN_ROOM_TYPE:
                rooms = sr.get_other_rooms()
            else:
                rooms = sr.get_private_rooms()
                
                
            if len(rooms) == 0:
                await message.channel.send(f"There are no {Race.Race.getWWFullName(ww_type)} rooms playing right now.")
                return
            
            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in {common.LEFT_ARROW_EMOTE, common.RIGHT_ARROW_EMOTE}
        
            embed_page_start_time = datetime.now()
            sent_missing_perms_message = False
            current_page = 0
            curRoomTxt = SimpleRooms.SimpleRooms.get_embed_text_for_race(rooms, current_page)
            should_send_error_message = False
            msg = await message.channel.send(curRoomTxt)
            await msg.add_reaction(common.LEFT_ARROW_EMOTE)
            await msg.add_reaction(common.RIGHT_ARROW_EMOTE)
            while (datetime.now() - embed_page_start_time) < common.embed_page_time:
    
                timeout_time_delta = common.embed_page_time - (datetime.now() - embed_page_start_time)
                timeout_seconds = timeout_time_delta.total_seconds()
                if timeout_seconds <= 0:
                    break
    
                try:
                    reaction, user = await client.wait_for('reaction_add', timeout=timeout_seconds, check=check)
                    if(str(reaction.emoji) == common.LEFT_ARROW_EMOTE):
                        current_page = (current_page - 1) % (len(rooms))
                    else:
                        current_page = (current_page + 1) % (len(rooms))
    
                    curRoomTxt = SimpleRooms.SimpleRooms.get_embed_text_for_race(rooms, current_page)                
    
                    try:
                        await msg.edit(content=curRoomTxt)
                    except discord.errors.Forbidden:
                        should_send_error_message = True
                    except discord.errors.NotFound:
                        break
                    
                    if should_send_error_message:
                        send_missing_permissions(message.channel)
                        sent_missing_perms_message = True
                except asyncio.TimeoutError:
                    break
            
            try:
                await msg.clear_reaction(common.LEFT_ARROW_EMOTE)
                await msg.clear_reaction(common.RIGHT_ARROW_EMOTE)
            except discord.errors.Forbidden:
                try:
                    await msg.remove_reaction(common.LEFT_ARROW_EMOTE, client.user)
                    await msg.remove_reaction(common.RIGHT_ARROW_EMOTE, client.user)
                except:
                    pass
                if message.guild is not None and not sent_missing_perms_message:
                    await send_missing_permissions(message.channel)
            except discord.errors.NotFound:
                pass
    
    
    @staticmethod
    async def vr_command_get_races(rLID:str, temp_bot):
        successful = await temp_bot.load_room_smart([rLID])
        if not successful:
            return None
        return temp_bot.getRoom().get_races_abbreviated(last_x_races=12)
    
    @staticmethod
    def vr_command_get_data(data_piece):
        place = -1
        if data_piece[1][0].isnumeric():
            place = int(data_piece[1][0])
        return  place, data_piece[0], str(data_piece[1][1]), UserDataProcessing.lounge_get(data_piece[0])
    

    @staticmethod           
    async def vr_command(this_bot:TableBot.ChannelBot, message:discord.Message, args:List[str], old_command:str, temp_bot):
        rlCooldown = this_bot.getRLCooldownSeconds()
        if rlCooldown > 0:
            delete_me = await message.channel.send(f"Wait {rlCooldown} more seconds before using this command.")
            await delete_me.delete(delay=5)
            return
        
    
        this_bot.updateRLCoolDown()
        message2 = await message.channel.send("Verifying room...")
        #Case 1: No mention, get FCs for the user - this happens when len(args) = 3
        #Case 2: Mention, get FCs for the mentioned user, this happens when len(args) > 3 and len(mentions) > 1
        #Case 3: FC: No mention, len(args) > 3, and is FC
        #Case 4: rLID: No mention, len(args) > 3, is rLID
        #Case 5: Lounge name: No mention, len(args) > 3, neither rLID nor FC
        successful = False
        room_data = None
        rLID = None
        if len(args) == 1:
            discordIDToLoad = str(message.author.id)
            await updateData(* await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad]) )
            FCs = UserDataProcessing.get_all_fcs(discordIDToLoad)
            successful, room_data, last_match_str, rLID = await this_bot.verify_room([FCs])
            if not successful:
                await message.channel.send("Could not find you in a room. (This could be an error if I couldn't find your FC.)")
        elif len(args) > 1:
            if len(message.raw_mentions) > 0:
                discordIDToLoad = str(message.raw_mentions[0])
                await updateData(* await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad]))
                FCs = UserDataProcessing.get_all_fcs(discordIDToLoad)
                successful, room_data, last_match_str, rLID = await this_bot.verify_room([FCs])
                if not successful:
                    await message.channel.send(f"Could not find {UtilityFunctions.process_name(str(message.mentions[0].name))} in a room. (This could be an error if I couldn't find their FC in the database.)")                      
            elif _is_fc(args[1]):
                successful, room_data, last_match_str, rLID = await this_bot.verify_room([args[1]])
                if not successful:
                    await message.channel.send("Could not find this FC in a room.")
            else:
                await updateData( * await LoungeAPIFunctions.getByLoungeNames([" ".join(old_command.split()[1:])]))
                FCs = UserDataProcessing.getFCsByLoungeName(" ".join(old_command.split()[1:]))
                
                successful, room_data, last_match_str, rLID = await this_bot.verify_room([FCs])
                if not successful:
                    await message.channel.send(f"Could not find {UtilityFunctions.process_name(' '.join(old_command.split()[1:]))} in a room. (This could be an error if I couldn't their FC in the database.)")             
        
        if not successful or room_data is None or rLID is None:
            await message2.delete()
            return
        FC_List = [fc for fc in room_data]
        await updateData(* await LoungeAPIFunctions.getByFCs(FC_List))
    

        tuple_data = [OtherCommands.vr_command_get_data(item) for item in room_data.items()]
        tuple_data.sort()
        
        str_msg =  f"```diff\n- {last_match_str.strip()} -\n\n"
        str_msg += '+{:>3} {:<13}| {:<13}| {:<1}\n'.format("#.", "Lounge Name", "Mii Name", "FC") 
        for place, FC, mii_name, lounge_name in tuple_data:
            if lounge_name == "":
                lounge_name = "UNKNOWN"
            str_msg += "{:>4} {:<13}| {:<13}| {:<1}\n".format(str(place)+".",lounge_name, mii_name, FC)
        
        #string matching isn't the safest way here, but this is an add-on feature, and I don't want to change 
        #the verify_room function
        if "(last start" in last_match_str:
            #go get races from room
            races_str = await OtherCommands.vr_command_get_races(rLID, temp_bot)
            if races_str is not None:
                str_msg += "\n\nRaces (Last 12): " + races_str
            else:
                str_msg += "\n\nFailed"
                
        await message.channel.send(f"{str_msg}```")
        await message2.delete()
             


 
class LoungeCommands:
    
    @staticmethod
    def has_authority_in_server_check(author, failure_message, authority_check=common.author_is_lounge_staff):
        if not authority_check(author):
            raise TableBotExceptions.NotStaff(failure_message)
        return True
    
    
    @staticmethod
    def correct_server_check(guild, failure_message, server_id=common.MKW_LOUNGE_SERVER_ID):
        if guild.id != server_id:
            raise TableBotExceptions.WrongServer(failure_message)
        return True
    
    @staticmethod
    def updater_channel_check(channel, failure_message, valid_channel_ids={common.MKW_LOUNGE_RT_UPDATER_CHANNEL, common.MKW_LOUNGE_CT_UPDATER_CHANNEL}):
        if channel.id not in valid_channel_ids:
            raise TableBotExceptions.WrongUpdaterChannel(failure_message)
        return True
    
    

    
    @staticmethod
    async def get_lock_command(message:discord.Message, this_bot:TableBot.ChannelBot):
        LoungeCommands.correct_server_check(message.guild, "cannot display lock")
        
        if this_bot.getRoom() is None or this_bot.getRoom().getSetupUser() is None:
            await message.channel.send("Bot is not locked to any user.")
            return
    
        room_lounge_names = this_bot.getRoom().get_loungenames_can_modify_table()
        to_send = "The bot is locked to players in this room: **"
        to_send += ", ".join(room_lounge_names)
        to_send += "**.\n"
        to_send += "The setup user who has the main lock is **" + str(this_bot.getRoom().getSetupUser()) + f"- {this_bot.getRoom().set_up_user_display_name}**"
        
        await message.channel.send(to_send)   
        
    @staticmethod
    async def transfer_lock_command(message:discord.Message, args:List[str], this_bot:TableBot.ChannelBot):
        LoungeCommands.correct_server_check(message.guild, "cannot transfer lock")
        LoungeCommands.has_authority_in_server_check(message.author, "cannot transfer lock")
        
        if this_bot.getRoom() is None or this_bot.getRoom().getSetupUser() is None:
            await message.channel.send("Cannot transfer lock. Bot not locked to any user.")
            return
    
        if len(args) <= 1:
            await message.channel.send("You must give their Discord ID. This is the long number you can get in Discord's Developer Mode.")       
            return
    
        newUser = args[1]
        if not newUser.isnumeric():
            await message.channel.send("You must give their Discord ID. This is the long number you can get in Discord's Developer Mode.")
            return
    
        newUser = int(newUser)
        this_bot.getRoom().set_up_user = newUser
        this_bot.getRoom().set_up_user_display_name = ""
        await message.channel.send("Lock transferred to: " + str(newUser))

    
    #TODO: Refactor this - in an rushed effort to release this, the code is sloppy.
    #It should be refactored as this is some of the worst code in TableBot
    
    @staticmethod
    async def __mogi_update__(client, this_bot:TableBot.ChannelBot, message:discord.Message, args:List[str], lounge_server_updates:Lounge.Lounge, is_primary=True):
        command_incorrect_format_message = "The format of this command is: `?" + args[0] + " TierNumber RacesPlayed (TableText)`\n- **TierNumber** must be a number. For RTs, between 1 and 8. For CTs, between 1 and 6. If you are trying to submit a squadqueue table, **TierNumber** should be: squadqueue\n-**RacesPlayed** must be a number, between 1 and 32."
        cooldown = lounge_server_updates.get_user_update_submit_cooldown(message.author.id)
        updater_channel_id, updater_link, preview_link, type_text = lounge_server_updates.get_information(is_primary)
        
        if cooldown > 0:
            await message.channel.send("You have already submitted a table very recently. Please wait " + str(cooldown) + " more seconds before submitting another table.", delete_after=10)
            return
        
        if len(args) < 3:
            await message.channel.send(command_incorrect_format_message)
            return
        

        tier_number, summary_channel_id = MogiUpdate.get_tier_and_summary_channel_id(args[1], is_primary)
        if tier_number is None:
            await message.channel.send(command_incorrect_format_message)
            return
        
        races_played = args[2]
        if not races_played.isnumeric() or int(args[2]) < 1 or int(args[2]) > 32:
            await message.channel.send(command_incorrect_format_message)
            return
        races_played = int(args[2])
        
        table_text = ""
        
        if len(args) == 3:
            if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
                await message.channel.send("Room is not loaded. You must have a room loaded if you do not give TableText to this command. Otherwise, do `?" + args[0] + " TierNumber RacesPlayed TableText`")
                return
            else:
                table_text, _ = SK.get_war_table_DCS(this_bot, use_lounge_otherwise_mii=True, use_miis=False, lounge_replace=True, server_id=message.guild.id, discord_escape=True)
        else:
            temp = message.content
            command_removed = temp[temp.lower().index(args[0])+len(args[0]):].strip("\n\t ")
            tier_number_removed = command_removed[command_removed.lower().index(args[1])+len(args[1]):].strip("\n\t ")
            table_text = command_removed[tier_number_removed.lower().index(args[2])+len(args[2]):].strip("\n\t ")
            
                    
            
        
    
        lounge_server_updates.update_user_cooldown(message.author)
        delete_me = await message.channel.send("Submitting table... please wait...")

        
        error_code, newTableText, json_data = await MogiUpdate.textInputUpdate(table_text, tier_number, races_played, is_rt=is_primary)
        
        
        if error_code != MogiUpdate.SUCCESS_EC:
            if error_code is None:
                await message.channel.send("Couldn't submit table. An unknown error occurred.")
            elif error_code == MogiUpdate.PLAYER_NOT_FOUND_EC:
                missing_players = json_data
                await message.channel.send("Couldn't submit table. The following players could not be found: **" + "**, **".join(missing_players) + "**\nCheck your submission for correct names. If your table has subs, they must be in this format: Sarah(4)/Jacob(8)")
            else:
                await message.channel.send("Couldn't submit table. Reason: *" + MogiUpdate.table_text_errors[error_code] + "*")
    
        
        else:
            url_table_text = urllib.parse.quote(newTableText)
            image_url = common.base_url_lorenzi + url_table_text
            table_image_path = str(message.id) + ".png"
            image_download_success = await common.download_image(image_url, table_image_path)
            try:
                if not image_download_success:
                    await message.channel.send("Could not get image for table.")
                else:
                    updater_channel = client.get_channel(updater_channel_id)
                    preview_link += urllib.parse.quote(json_data)
                    updater_link += urllib.parse.quote(json_data)


                    embed = discord.Embed(
                                        title = "",
                                        description="[Click to preview this update]("+ updater_link + ")",
                                        colour = discord.Colour.dark_red()
                                    )
                    file = discord.File(table_image_path)
                    lounge_server_updates.add_counter()
                    id_to_submit = lounge_server_updates.get_counter()
                    embed.add_field(name='Submission ID', value=str(id_to_submit))
                    embed.add_field(name="Tier", value=tier_number)
                    embed.add_field(name="Races Played", value=races_played)
                    summary_channel = client.get_channel(summary_channel_id)
                    embed.add_field(name="Approving to", value=(summary_channel.mention if summary_channel is not None else "Can't find channel"))
                    embed.add_field(name='Submitted from', value=message.channel.mention)
                    embed.add_field(name='Submitted by', value=message.author.mention)
                    embed.add_field(name='Discord ID', value=str(message.author.id))
                    
                    shortened_admin_panel_link = "No Link"
                    try:
                        admin_link_tiny_url = await URLShortener.tinyurl_shorten_url(updater_link)
                        shortened_admin_panel_link = f"[Preview]({admin_link_tiny_url})"
                    except:
                        pass
                    
                    embed.add_field(name='Short Preview Link:', value=shortened_admin_panel_link)
                    
                    embed.set_image(url="attachment://" + table_image_path)
                    embed.set_author(name="Updater Automation", icon_url="https://64.media.tumblr.com/b0df9696b2c8388dba41ad9724db69a4/tumblr_mh1nebDwp31rsjd4ho1_500.jpg")                        
                    
                    sent_message = await updater_channel.send(file=file, embed=embed)
                    lounge_server_updates.add_report(id_to_submit, sent_message, summary_channel_id)
                
                    
                    file = discord.File(table_image_path)
                    embed = discord.Embed(
                                        title = "Successfully submitted to " + type_text + " Reporters and " + type_text + " Updaters",
                                        description="[Click to preview this update]("+ preview_link + ")",
                                        colour = discord.Colour.dark_red()
                                    )
                    embed.add_field(name='Submission ID', value=str(id_to_submit))
                    embed.add_field(name='Races Played', value=str(races_played))
                    
                    
                    shortened_preview_link = "No Link"
                    try:
                        if updater_link == preview_link:
                            shortened_preview_link = shortened_admin_panel_link
                        else:
                            preview_link_tiny_url = await URLShortener.tinyurl_shorten_url(preview_link)
                            shortened_preview_link = f"[Preview]({preview_link_tiny_url})"
                    except:
                        pass
                    
                    embed.add_field(name='Short Preview Link:', value=shortened_preview_link)
                    
                    embed.set_image(url="attachment://" + table_image_path)
                    embed.set_author(name="Updater Automation", icon_url="https://64.media.tumblr.com/b0df9696b2c8388dba41ad9724db69a4/tumblr_mh1nebDwp31rsjd4ho1_500.jpg")
                    embed.set_footer(text="Note: the actual update may look different than this preview if the Updaters need to first update previous mogis. If the link is too long, just hit the enter key.")
                    
                    await message.channel.send(file=file, embed=embed)
            finally:
                if os.path.exists(table_image_path):
                    os.remove(table_image_path)
        lounge_server_updates.update_user_cooldown(message.author)
        await delete_me.delete()
    
    @staticmethod
    async def ct_mogi_update(client, this_bot:TableBot.ChannelBot, message:discord.Message, args:List[str], lounge_server_updates:Lounge.Lounge):
        LoungeCommands.correct_server_check(message.guild, "cannot submit table update for CT mogi", lounge_server_updates.server_id)
        await LoungeCommands.__mogi_update__(client, this_bot, message, args, lounge_server_updates, is_primary=False)
        
        
    @staticmethod
    async def rt_mogi_update(client, this_bot:TableBot.ChannelBot, message:discord.Message, args:List[str], lounge_server_updates:Lounge.Lounge):
        LoungeCommands.correct_server_check(message.guild, "cannot submit table update for RT mogi", lounge_server_updates.server_id)
        await LoungeCommands.__mogi_update__(client, this_bot, message, args, lounge_server_updates, is_primary=True)
    
    
    @staticmethod
    async def __submission_action_command__(client, message:discord.Message, args:List[str], lounge_server_updates:Lounge.Lounge, is_approval=True):
        if len(args) < 2:
            await message.channel.send("The way to use this command is: ?" + args[0] + " submissionID")
            return
        
        submissionID = args[1]
        if submissionID.isnumeric():
            submissionID = int(submissionID)
            if lounge_server_updates.has_submission_id(submissionID):
                submissionMessageID, submissionChannelID, summaryChannelID, submissionStatus = lounge_server_updates.get_submission_id(submissionID)
                submissionMessage = None
                
                try:
                    submissionChannel = client.get_channel(submissionChannelID)
                    if submissionChannel is None:
                        await message.channel.send("I cannot see the submission channels (or they changed). Get boss help.")
                        return
                    submissionMessage = await submissionChannel.fetch_message(submissionMessageID)
                except discord.errors.NotFound:
                    await message.channel.send("That submission appears to have been deleted on Discord. I have now removed this submission from my records.")
                    lounge_server_updates.remove_submission_id(submissionID)
                    return
                
                if is_approval:
                    submissionEmbed = submissionMessage.embeds[0]
                    submissionEmbed.remove_field(6)
                    submissionEmbed.remove_field(5)
                    submissionEmbed.set_field_at(3, name="Approved by:", value=message.author.mention)
                    submissionEmbed.set_field_at(4, name="Approval link:", value="[Message](" + submissionMessage.jump_url + ")")
                    
                    summaryChannelRetrieved = True
                    if summaryChannelID is None:
                        summaryChannelRetrieved = False
                    summaryChannelObj = client.get_channel(summaryChannelID)
                    if summaryChannelObj is None:
                        summaryChannelRetrieved = False
                    if not summaryChannelRetrieved:
                        await message.channel.send("I cannot see the summary channels. Contact a boss.")
                        return
                    try:
                        await summaryChannelObj.send(embed=submissionEmbed)
                    except discord.errors.Forbidden:
                        await message.channel.send("I'm not allowed to send messages in summary channels. Contact a boss.")
                        return
                    
                    
                    lounge_server_updates.approve_submission_id(submissionID)
                    
                    await submissionMessage.clear_reaction("\u274C")
                    await submissionMessage.add_reaction("\u2705")
                    await message.add_reaction(u"\U0001F197")
                else:
                    await submissionMessage.clear_reaction("\u2705")
                    await submissionMessage.add_reaction("\u274C")
                    lounge_server_updates.deny_submission_id(submissionID)
                    await message.add_reaction(u"\U0001F197")
            else:
                await message.channel.send("I couldn't find this submission ID. Make sure you have the right submission ID.")                              
        else:
            await message.channel.send("The way to use this command is: ?" + args[0] + " submissionID - submissionID must be a number")


    @staticmethod
    async def approve_submission_command(client, message:discord.Message, args:List[str], lounge_server_updates:Lounge.Lounge):
        LoungeCommands.correct_server_check(message.guild, "cannot approve table submission", lounge_server_updates.server_id)
        LoungeCommands.has_authority_in_server_check(message.author, "cannot approve table submission", authority_check=lounge_server_updates.report_table_authority_check)
        LoungeCommands.updater_channel_check(message.channel, "cannot approve table submission", lounge_server_updates.get_updater_channel_ids())
        await LoungeCommands.__submission_action_command__(client, message, args, lounge_server_updates, is_approval=True)
        
    
    @staticmethod
    async def deny_submission_command(client, message:discord.Message, args:List[str], lounge_server_updates:Lounge.Lounge):
        LoungeCommands.correct_server_check(message.guild, "cannot deny table submission", lounge_server_updates.server_id)
        LoungeCommands.has_authority_in_server_check(message.author, "cannot deny table submission", authority_check=lounge_server_updates.report_table_authority_check)
        LoungeCommands.updater_channel_check(message.channel, "cannot deny table submission", lounge_server_updates.get_updater_channel_ids())
        await LoungeCommands.__submission_action_command__(client, message, args, lounge_server_updates, is_approval=False)
        
    
    @staticmethod
    async def pending_submissions_command(message:discord.Message, lounge_server_updates:Lounge.Lounge):
        LoungeCommands.correct_server_check(message.guild, "cannot display pending table submissions", lounge_server_updates.server_id)
        LoungeCommands.has_authority_in_server_check(message.author, "cannot display pending table submissions", authority_check=lounge_server_updates.report_table_authority_check)
       
        to_send = ""
        for submissionID in lounge_server_updates.table_reports:
            _, submissionChannelID, summaryChannelID, submissionStatus = lounge_server_updates.get_submission_id(submissionID)
            if submissionStatus == "PENDING":
                to_send += MogiUpdate.getTierFromChannelID(summaryChannelID) + " - Submission ID: " + str(submissionID) + "\n"
        if to_send == "":
            to_send = "No pending submissions."
        await message.channel.send(to_send)

        
        

"""================== Server Administrator Settings Commands ==============="""
#TODO: Refactor these - target the waterfall-like if-statements
class ServerDefaultCommands:
    """There is no point to this class, other than for organization purposes.
    This class contains all of the commands that server administrators can use to set defaults for their server"""
    
    @staticmethod
    def server_admin_check(author, failure_message):
        if not author.guild_permissions.administrator:
            raise TableBotExceptions.NotServerAdministrator(failure_message)
        return True
    
    @staticmethod
    async def large_time_setting_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str):
        if not common.running_beta:
            ServerDefaultCommands.server_admin_check(message.author, "cannot change server default for hiding large times on tables")
        
        server_id = message.guild.id
    
        if len(args) == 1:
            await send_available_large_time_options(message, args, this_bot, server_prefix, server_wide=True)
            return
        
        elif len(args) > 1:
            setting = args[1]
            if setting not in ServerFunctions.bool_map:
                await message.channel.send(f"That is not a valid default large time setting. To see valid settings, run the command `{server_prefix}{args[0]}` and read carefully.")
                return
            
            was_success = ServerFunctions.change_default_large_time_setting(server_id, setting)
            if was_success:
                await message.channel.send(f"Server setting changed to:\n{get_large_time_option(setting)}")
            else:
                await message.channel.send("Error changing default large time setting for this server. This is TableBot's fault. Try to set it again.")

    @staticmethod              
    async def mii_setting_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str):
        if not common.running_beta:
            ServerDefaultCommands.server_admin_check(message.author, "cannot change miis default for this server")

        server_id = message.guild.id
    
        if len(args) == 1:
            await send_available_mii_options(message, args, this_bot, server_prefix, server_wide=True)
            return
        
        elif len(args) > 1:
            setting = args[1]
            if setting not in ServerFunctions.bool_map:
                await message.channel.send(f"That is not a valid mii setting. To see valid settings, run the command `{server_prefix}{args[0]}` and read carefully.")
                return
            
            was_success = ServerFunctions.change_default_server_mii_setting(server_id, setting)
            if was_success:
                await message.channel.send(f"Server setting changed to:\n{get_mii_option(setting)}")
            else:
                await message.channel.send("Error changing mii on/off default for server. This is TableBot's fault. Try to set it again.")


    @staticmethod
    async def graph_setting_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str):
        if not common.running_beta:
            ServerDefaultCommands.server_admin_check(message.author, "cannot change default graph for this server")

        server_id = message.guild.id
        if len(args) == 1:
            await send_available_graph_list(message, args, this_bot, server_prefix, server_wide=True)
            return
        
        if len(args) > 1:
            setting = args[1]
            if not this_bot.is_valid_graph(setting):
                await message.channel.send(f"That is not a valid graph setting. To see valid settings, run the command `{server_prefix}{args[0]}` and read carefully.")
                return
            
            was_success = ServerFunctions.change_default_server_graph(server_id, setting)
            if was_success:
                await message.channel.send(f"Default graph for server set to: **{this_bot.get_graph_name(setting)}**")
            else:
                await message.channel.send("Error setting default graph for server. This is TableBot's fault. Try to set it again.")

    @staticmethod
    async def theme_setting_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str):
        if not common.running_beta:
            ServerDefaultCommands.server_admin_check(message.author, "cannot change default table theme for this server")
        
        server_id = message.guild.id
        if len(args) == 1:
            await send_table_theme_list(message, args, this_bot, server_prefix, server_wide=True)
            return
        if len(args) > 1:
            setting = args[1]
            if not this_bot.is_valid_style(setting):
                await message.channel.send(f"That is not a valid table theme setting. To see valid settings, run the command `{server_prefix}{args[0]}` and read carefully.")
                return
            
            was_success = ServerFunctions.change_default_server_table_theme(server_id, setting)
            if was_success:
                await message.channel.send(f"Default table theme for server set to: **{this_bot.get_style_name(setting)}**")
            else:
                await message.channel.send("Error setting default table theme for server. This is TableBot's fault. Try to set it again.")
     

    @staticmethod
    async def change_server_prefix_command(message:discord.Message, args:List[str]):
        ServerDefaultCommands.server_admin_check(message.author, "cannot change prefix")
        server_id = message.guild.id
        
        if len(args) < 2:
            await message.channel.send("Give a prefix. Prefix not changed.")
            return
    
        end_prefix_cmd = message.content.lower().index("setprefix") + len("setprefix")
        new_prefix = message.content[end_prefix_cmd:].strip("\n").strip()
        if len(new_prefix) < 1:
            await message.channel.send("Cannot set an empty prefix. Prefix not changed.")
            return
        if len(new_prefix) > common.MAX_PREFIX_LENGTH:
            await message.channel.send(f"Prefixes must be {common.MAX_PREFIX_LENGTH} characters or less.")
            return

        was_success = ServerFunctions.change_server_prefix(str(server_id), new_prefix)
        if was_success:
            await message.channel.send("Prefix changed to: " + new_prefix) 
        else:
            await message.channel.send("Errors setting prefix. Prefix not changed.")


"""================== Tabling Commands =================="""
#TODO: Refactor these
class TablingCommands:
    
    @staticmethod
    async def reset_command(message:discord.Message, table_bots):
        server_id = message.guild.id
        channel_id = message.channel.id
        del(table_bots[server_id][channel_id])
        await message.channel.send("Reset successful.")
    
    @staticmethod
    async def display_races_played_command(message:discord.Message, this_bot:ChannelBot, server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        else:
            await message.channel.send(this_bot.getRoom().get_races_string())
                    
                    
    @staticmethod
    async def fcs_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        else:
            await message.channel.send(this_bot.getRoom().getFCPlayerListString())
    
    
    @staticmethod
    async def rxx_command(message:discord.Message, this_bot:ChannelBot, server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        else:
            await message.channel.send(this_bot.getRoom().getRXXText())   


    @staticmethod
    async def team_penalty_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return

        if this_bot.getWar().is_ffa():
            await message.channel.send("You can't give team penalties in FFAs. Do " + server_prefix + "penalty to give an individual player a penalty in an FFA.")
            return
        
        if len(args) == 1:
            teams = sorted(this_bot.getWar().getTags())
            to_send = ""
            for team_num, team in enumerate(teams, 1):
                to_send += UtilityFunctions.process_name(str(team_num)) + ". " + team + "\n"
            to_send += "\n**To give the 2nd team on the list a 15 point penalty:** *" + server_prefix + "teampenalty 2 15*"
            await message.channel.send(to_send)
            return
        
        if len(args) != 3:
            await message.channel.send(example_help(server_prefix, args[0]))
            return
    
        teamNum = args[1]
        amount = args[2]
        teams = sorted(this_bot.getWar().getTags())
        if not teamNum.isnumeric():
            for ind, team in enumerate(teams):
                if team.lower() == teamNum:
                    teamNum = ind + 1
                    break
        else:
            teamNum = int(teamNum)
        if not amount.isnumeric():
            if len(amount) > 0 and amount[0] == '-':
                if amount[1:].isnumeric():
                    amount = int(amount[1:]) * -1
        else:
            amount = int(amount)
        
        
        if not isinstance(teamNum, int) or not isinstance(amount, int):
            await message.channel.send(f"Both the team number and the penalty amount must be numbers. {example_help(server_prefix, args[0])}")
        elif teamNum < 1 or teamNum > len(teams):
            await message.channel.send(f"The team number must be on this list (between 1 and {len(teams)}). {example_help(server_prefix, args[0])}")
        else:
            this_bot.add_save_state(message.content)
            this_bot.getWar().addTeamPenalty(teams[teamNum-1], amount)
            await message.channel.send(UtilityFunctions.process_name(teams[teamNum-1] + " given a " + str(amount) + " point penalty."))

    
    
    
    
    @staticmethod
    async def disconnections_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
        
        if len(args) == 1:
            had_DCS, DC_List_String = this_bot.getRoom().getDCListString(this_bot.getWar().getNumberOfGPS(), True)
            if had_DCS:
                DC_List_String += "\nIf the first disconnection on this list was on results: **" + server_prefix + "dc 1 onresults**\n" +\
                "If they were not on results, do **" + server_prefix + "dc 1 before**"
            await message.channel.send(DC_List_String)  
            return
    
        if len(args) < 3:
            await message.channel.send("You must give a dc number on the list and if they were on results or not. Run " + server_prefix + "dcs for more information.")
            return
    
        missing_per_race = this_bot.getRoom().getMissingOnRace(this_bot.getWar().numberOfGPs)
        merged = list(itertools.chain(*missing_per_race))
        disconnection_number = args[1]
        if not disconnection_number.isnumeric():
            await message.channel.send(UtilityFunctions.process_name(str(disconnection_number)) + " is not a number on the dcs list. Do " + server_prefix + "dcs for an example on how to use this command.")
            return
        if int(disconnection_number) > len(merged):
            await message.channel.send("There have not been this many DCs. Run " + server_prefix + "dcs to learn how to use this command.")  
            return
        if int(disconnection_number) < 1:
            await message.channel.send("You must give a DC number on the list. Run " + server_prefix + "dcs to learn how to use this command.")  
            return
    
        disconnection_number = int(disconnection_number)
        on_or_before = args[2].lower().strip("\n").strip()
        race, index = 0, 0
        counter = 0
        for missing in missing_per_race:
            race += 1
            
            for _ in missing:
                counter += 1
                if counter == disconnection_number:
                    break
                index+=1

            else:
                index=0
                continue
            break
        
        player_fc = missing_per_race[race-1][index][0]
        player_name = UtilityFunctions.process_name(str(missing_per_race[race-1][index][1]) + lounge_add(player_fc))
        if on_or_before in ["on", "during", "midrace", "results", "onresults"]:
            this_bot.add_save_state(message.content)
            this_bot.getRoom().dc_on_or_before[race][player_fc] = 'on'
            await message.channel.send("Saved: " + player_name + ' was on results for race #' + str(race))                    
            return
        if on_or_before in ["before", "prior", "beforerace", "notonresults", "noresults", "off"]:
            this_bot.add_save_state(message.content)
            this_bot.getRoom().dc_on_or_before[race][player_fc] = 'before'
            await message.channel.send("Saved: " + player_name + ' was not on results for race #' + str(race))                    
            return
        
        await message.channel.send('"' + UtilityFunctions.process_name(str(on_or_before)) + '" needs to be either "on" or "before". Do ' + server_prefix + "dcs for an example on how to use this command.")



    @staticmethod
    async def player_penalty_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        if len(args) == 1:
            to_send = this_bot.getRoom().get_sorted_player_list_string()
            to_send += "\n**To give the 2nd player on the list a 15 point penalty:** *" + server_prefix + "penalty 2 15*"
            await message.channel.send(to_send)
            return
        
        if len(args) != 3:
            await message.channel.send(example_help(server_prefix, args[0]))
            return
        
        playerNum = args[1]
        amount = args[2]
        players = this_bot.getRoom().get_sorted_player_list()
        if not playerNum.isnumeric():
            pass
        else:
            playerNum = int(playerNum)
        if not amount.isnumeric():
            if len(amount) > 0 and amount[0] == '-':
                if amount[1:].isnumeric():
                    amount = int(amount[1:]) * -1
        else:
            amount = int(amount)
            
        if not isinstance(playerNum, int) or not isinstance(amount, int):
            await message.channel.send(f"Both player number and the penalty amount must be numbers. {example_help(server_prefix, args[0])}")
        elif playerNum < 1 or playerNum > len(players):
            await message.channel.send(f"The player number must be on this list (between 1 and {len(players)}). {example_help(server_prefix, args[0])}")
        else:
            this_bot.add_save_state(message.content)
            this_bot.getRoom().addPlayerPenalty(players[playerNum-1][0], amount)
            await message.channel.send(UtilityFunctions.process_name(players[playerNum-1][1] + lounge_add(players[playerNum-1][0]) + " given a " + str(amount) + " point penalty."))


    @staticmethod
    async def change_player_score_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool, command:str):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return

        if len(args) == 1:
            to_send = this_bot.getRoom().get_sorted_player_list_string()
            to_send += "\n**To edit the GP3 score of the 7th player on the list to 37 points:** *" + server_prefix + "edit 7 3 37*"
            await message.channel.send(to_send)
            return
        
        if len(args) != 4:
            await message.channel.send("Do " + server_prefix + "edit for an example on how to use this command.")
            return
    
    
        playerNum = command.split()[1].strip()
        GPNum = args[2]
        amount = args[3]
        players = this_bot.getRoom().get_sorted_player_list()
        if not GPNum.isnumeric() or not amount.isnumeric():
            await message.channel.send("GP Number and amount must all be numbers. Do " + server_prefix + "edit for an example on how to use this command.")
            return

        players = this_bot.getRoom().get_sorted_player_list()
        numGPs = this_bot.getWar().numberOfGPs
        GPNum = int(GPNum)
        amount = int(amount)
        if playerNum.isnumeric():
            playerNum = int(playerNum)
            if playerNum < 1 or playerNum > len(players):
                await message.channel.send("The player number must be on this list (between 1 and " + str(len(players)) + "). Do " + server_prefix + "edit for an example on how to use this command.")
            elif GPNum < 1 or GPNum > numGPs:
                await message.channel.send("The current war is only set to " + str(numGPs) + " GPs. Your GP number was: " + UtilityFunctions.process_name(str(GPNum)))
            else:
                this_bot.add_save_state(message.content)
                this_bot.getWar().addEdit(players[playerNum-1][0], GPNum, amount)
                await message.channel.send(UtilityFunctions.process_name(players[playerNum-1][1] + lounge_add(players[playerNum-1][0]) + " GP" + str(GPNum) + " score edited to " + str(amount) + " points."))
        else:
            lounge_name = str(copy.copy(playerNum))
            loungeNameFCs = UserDataProcessing.getFCsByLoungeName(lounge_name)
            for _playerNum, (fc, _) in enumerate(players, 1):
                if fc in loungeNameFCs:
                    break
            else:
                _playerNum = None
                
                
            if _playerNum is None:
                await message.channel.send("Could not find Lounge name " + UtilityFunctions.process_name(str(lounge_name)) + " in this room.")
            else:
                this_bot.add_save_state(message.content)
                this_bot.getWar().addEdit(players[_playerNum-1][0], GPNum, amount)
                await message.channel.send(UtilityFunctions.process_name(players[_playerNum-1][1] + lounge_add(players[_playerNum-1][0]) + " GP" + str(GPNum) + " score edited to " + str(amount) + " points."))



    #Code is quite similar to chane_player_tag_command, potential refactor opportunity?
    @staticmethod
    async def change_player_name_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool, command:str):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        if len(args) < 3:
            to_send = this_bot.getRoom().get_sorted_player_list_string()
            to_send += "\n**To change the name of the 8th player on the list to \"joe\", do:** *" + server_prefix + "changename 8 joe*"
            await message.channel.send(to_send)
            return


        playerNum = command.split()[1].strip()
        new_name = " ".join(command.split()[2:])
        players = this_bot.getRoom().get_sorted_player_list()
        if playerNum.isnumeric():
            playerNum = int(playerNum)
            if playerNum < 1 or playerNum > len(players):
                await message.channel.send("The player number must be on this list (between 1 and " + str(len(players)) + "). Do " + server_prefix + "changename for an example on how to use this command.")
            else:
                this_bot.add_save_state(message.content)
                this_bot.getRoom().setNameForFC(players[playerNum-1][0], new_name)
                await message.channel.send(UtilityFunctions.process_name(players[playerNum-1][1] + lounge_add(players[playerNum-1][0])) + " name set to: " + UtilityFunctions.process_name(new_name))
        else:
            lounge_name = str(copy.copy(playerNum))
            loungeNameFCs = UserDataProcessing.getFCsByLoungeName(lounge_name)
            for _playerNum, (fc, _) in enumerate(players, 1):
                if fc in loungeNameFCs:
                    break
            else:
                _playerNum = None
                
                
            if _playerNum is None:
                await message.channel.send("Could not find Lounge name " + UtilityFunctions.process_name(str(lounge_name)) + " in this room.")
            else:
                this_bot.add_save_state(message.content)
                this_bot.getRoom().setNameForFC(players[_playerNum-1][0], new_name)
                await message.channel.send(UtilityFunctions.process_name(players[_playerNum-1][1] + lounge_add(players[_playerNum-1][0])) + " name set to: " + UtilityFunctions.process_name(new_name))

    @staticmethod
    async def change_player_tag_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool, command:str):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
        

        if this_bot.getWar().is_ffa():
            to_send = "You cannot change a player's tag in an FFA. FFAs have no teams."
            await message.channel.send(to_send)
            return
        
        if len(args) < 3:
            to_send = this_bot.getRoom().get_sorted_player_list_string()
            to_send += "\n**To change the tag of the 8th player on the list to KG, do:** *" + server_prefix + "changetag 8 KG*"
            await message.channel.send(to_send)
            return
        
        elif len(args) >= 3:
            playerNum = command.split()[1].strip()
            new_tag = " ".join(command.split()[2:])
            players = this_bot.getRoom().get_sorted_player_list()
            if playerNum.isnumeric():
                playerNum = int(playerNum)
                if playerNum < 1 or playerNum > len(players):
                    await message.channel.send("The player number must be on this list (between 1 and " + str(len(players)) + "). Do " + server_prefix + "changetag for an example on how to use this command.")
                else:
                    this_bot.add_save_state(message.content)
                    this_bot.getWar().setTeamForFC(players[playerNum-1][0], new_tag)
                    await message.channel.send(UtilityFunctions.process_name(players[playerNum-1][1] + lounge_add(players[playerNum-1][0])) + " tag set to: " + UtilityFunctions.process_name(new_tag))
            else:
                lounge_name = str(copy.copy(playerNum))
                loungeNameFCs = UserDataProcessing.getFCsByLoungeName(lounge_name)
                for _playerNum, (fc, _) in enumerate(players, 1):
                    if fc in loungeNameFCs:
                        break
                else:
                    _playerNum = None
                    
                    
                if _playerNum is None:
                    await message.channel.send("Could not find Lounge name " + UtilityFunctions.process_name(str(lounge_name)) + " in this room.")
                else:
                    this_bot.add_save_state(message.content)
                    this_bot.getWar().setTeamForFC(players[_playerNum-1][0], new_tag)
                    await message.channel.send(UtilityFunctions.process_name(players[_playerNum-1][1] + lounge_add(players[_playerNum-1][0])) + " tag set to: " + UtilityFunctions.process_name(new_tag))


    #Refactor this method to make it more readable
    @staticmethod
    async def start_war_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool, command:str, permission_check:Callable):
        server_id = message.guild.id
        author_id = message.author.id
        if not is_lounge_server or permission_check(message.author) or (len(args) - command.count(" gps=") - command.count(" sui=") - command.count(" psb=")) <= 3:
            if len(args) < 3:
                #TODO: sui=yes = psb
                await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            else:
                rlCooldown = this_bot.getRLCooldownSeconds()
                if rlCooldown > 0:
                    delete_me = await message.channel.send(f"Wait {rlCooldown} more seconds before using this command.")
                    await delete_me.delete(delay=5)
                else:
                    this_bot.reset(server_id)
                    this_bot.updateRLCoolDown()
                    
                    warFormat = args[1]
                    numTeams = args[2]
                    numGPsPos, numgps = getNumGPs(args)
                    iLTPos, ignoreLargeTimes = getSuppressLargeTimes(args)
                    useMiis, _, miisPos = getUseMiis(args, True, 3)
                    if iLTPos >= 0 and 'sui=' in command:
                        await message.channel.send("*sui= will change to psb= in later updates. Use psb=yes or professionalseriesbagging=yes in the future*")
                    
                    if miisPos < 0:
                        useMiis = ServerFunctions.get_server_mii_setting(server_id)
                    if iLTPos < 0:
                        ignoreLargeTimes = ServerFunctions.get_server_large_time_setting(server_id)
                    
                    message2 = await message.channel.send("Loading room...")
                    #This is the background task for getting miis, it will be awaited once everything in ?sw finishes
                    populate_mii_task = None
                    #Case 1: No mention, get FCs for the user - this happens when len(args) = 3
                    #Case 2: Mention, get FCs for the mentioned user, this happens when len(args) > 3 and len(mentions) > 1
                    #Case 3: FC: No mention, len(args) > 3, and is FC
                    #Case 4: rLID: No mention, len(args) > 3, is rLID
                    #Case 5: Lounge name: No mention, len(args) > 3, neither rLID nor FC
                    successful = False
                    discordIDToLoad = None
                    if len(args) == 3 or (len(args) > 3 and (numGPsPos == 3 or iLTPos == 3 or miisPos == 3)):
                        discordIDToLoad = str(author_id)
                        await updateData(* await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad]) )
                        FCs = UserDataProcessing.get_all_fcs(discordIDToLoad)
                        successful = await this_bot.load_room_smart([FCs])
                        if not successful:
                            await message.channel.send("Could not find you in a room. **Did you finish the first race?**")
                    elif len(args) > 3:
                        if len(message.raw_mentions) > 0:
                            discordIDToLoad = str(message.raw_mentions[0])
                            await updateData(* await LoungeAPIFunctions.getByDiscordIDs([discordIDToLoad]))
                            FCs = UserDataProcessing.get_all_fcs(discordIDToLoad)
                            successful = await this_bot.load_room_smart([FCs])
                            if not successful:
                                lookup_name = UtilityFunctions.process_name(str(message.mentions[0].name))
                                await message.channel.send(f"Could not find {lookup_name} in a room. **Did they finish the first race?**")                      
                        elif _is_rLID(args[3]):
                            successful = await this_bot.load_room_smart([args[3]])
                            if not successful:
                                await message.channel.send("Could not find this rxx number. Is the room over 24 hours old?")                                            
                        elif _is_fc(args[3]):
                            successful = await this_bot.load_room_smart([args[3]])
                            if not successful:
                                await message.channel.send("Could not find this FC in a room. **Did they finish the first race?**")
                        else:
                            their_name = ""
                            for arg in command.split()[3:]:
                                if '=' in arg:
                                    break
                                their_name += arg + " "
                            their_name = their_name.strip()
                            await updateData( * await LoungeAPIFunctions.getByLoungeNames([their_name]))
                            FCs = UserDataProcessing.getFCsByLoungeName(their_name)
                            successful = await this_bot.load_room_smart([FCs])
                            if not successful:
                                processed_lookup_name = UtilityFunctions.process_name(their_name)
                                await message.channel.send(f"Could not find {processed_lookup_name} in a room. **Did they finish the first race?**")                      
                    if successful:
                        this_bot.freeLock()
                        this_bot.getRoom().setSetupUser(author_id,  message.author.display_name)
                        try:
                            this_bot.setWar(War.War(warFormat, numTeams, numgps, ignoreLargeTimes=ignoreLargeTimes, displayMiis=useMiis))
                        except TableBotExceptions.InvalidWarFormatException:
                            this_bot.setWar(None)
                            await message.channel.send("War format was incorrect. Valid options: FFA, 1v1, 2v2, 3v3, 4v4, 5v5, 6v6. War not created.")
                        except TableBotExceptions.InvalidNumberOfPlayersException:
                            this_bot.setWar(None)
                            await message.channel.send("Too many players based on the teams and war format. War not created.")
                        else:  
                        
                            if this_bot.getWar() is not None:
                                populate_mii_task = asyncio.get_event_loop().create_task(this_bot.populate_miis(str(message.id)))
                                players = list(this_bot.getRoom().getFCPlayerListStartEnd(1, numgps*4).items())
                                player_fcs_tags, hasANoneTag = getTagsSmart(players, this_bot.getWar().playersPerTeam)
                                if hasANoneTag:
                                    player_fcs_tags = {}
                                    for fc_player in players:
                                        player_fcs_tags[fc_player] = getTagSmart(fc_player[1])
                                
                                #sort the fcs_tags by their tag
                                player_fcs_tags = sorted(player_fcs_tags.items(), key=lambda x: x[1])
                                if this_bot.getWar().formatting.lower() != "1v1" and this_bot.getWar().formatting.lower() != "ffa":
                                    teamTag = None
                                    to_print = ""
                                    previous_tags = []
                                    tag_counter = 0
                                    FC_List = [fc for fc, _ in players]
                                    await updateData(* await LoungeAPIFunctions.getByFCs(FC_List))
                                    for playerNum, ((fc, playerName), (_, playerTag)) in enumerate(player_fcs_tags):
                                        if len(playerTag.strip()) < 1:
                                            playerTag = str(playerNum+1)
                                        
                                        if (playerNum) % this_bot.getWar().playersPerTeam == 0:
                                            #Start a new team
                                            teamTag = playerTag
                                            if teamTag in previous_tags:
                                                tag_counter += 1
                                                teamTag = f"{teamTag}_{tag_counter}"
                                            else:
                                                tag_counter = 0
                                            previous_tags.append(teamTag)
                                            if playerTag is None:
                                                teamTag = f"**Team #{playerNum+1}\n**"
                                            cur_processed_team_tag = UtilityFunctions.process_name(teamTag)
                                            to_print += f"**Tag: {cur_processed_team_tag}** \n"
                                        temp_name = f"\t{playerNum+1}. {playerName}"
                                        if fc in UserDataProcessing.FC_DiscordID:
                                            DID = UserDataProcessing.FC_DiscordID[fc][0]
                                            if DID in UserDataProcessing.discordID_Lounges:
                                                lounge_name = UserDataProcessing.discordID_Lounges[DID]
                                                temp_name += f" - ({lounge_name})"
                                        
                                        to_print += UtilityFunctions.process_name(temp_name) + "\n"
                                        
                                    to_print += "\n***Is this correct?** (" + server_prefix + "yes or " + server_prefix + "no)*"
                                    
                                    await message.channel.send(to_print)
                                    this_bot.prev_command_sw = True
    
                                else:
                                    dummy_teams = {}
                                    
                                    for teamNumber in range(0, min(this_bot.getWar().numberOfTeams, len(players))):
                                        dummy_teams[players[teamNumber][0]] = str(teamNumber)
                                    this_bot.getWar().setTeams(dummy_teams)
                                    ffa_loaded_str = "FFA started. rxx: "
                                    if len(this_bot.getRoom().rLIDs) == 1:
                                        ffa_loaded_str += str(this_bot.getRoom().rLIDs[0])
                                    else:
                                        ffa_loaded_str += str(this_bot.getRoom().rLIDs)
                                        
                                    await message.channel.send(ffa_loaded_str)
                                
                                this_bot.setShouldSendNotification(True)
                    else:
                        this_bot.setWar(None)
                        this_bot.setRoom(None)
                    
                    await message2.delete()
                    if populate_mii_task is not None:
                        await populate_mii_task
        else:
            await message.channel.send(f"You can only load a room for yourself in Lounge. Do this instead: `{server_prefix}{args[0]} {args[1]} {args[2]}`")
     
     
     
    
    
    
    
    
    @staticmethod                  
    async def after_start_war_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str):
        this_bot.prev_command_sw = False
        this_bot.manualWarSetUp = False
        if args[0].lower().strip() not in ['yes', 'no', 'y', 'n']:
            this_bot.setWar(None)
            await message.channel.send(f"Please put {server_prefix}yes or {server_prefix}no to **Is this correct?** - War stopped.")   
            return
        
        if args[0].lower().strip() in ['no', 'n']:
            await message.channel.send(f"***Input the teams in the following format: *** Suppose for a 2v2v2, tag A is 2 and 3 on the list, B is 1 and 4, and Player is 5 and 6, you would enter:  *{server_prefix}A 2 3 / B 1 4 / Player 5 6*")
            this_bot.manualWarSetUp = True
            return
        
        if this_bot.getRoom() is None or not this_bot.getRoom().is_initialized():
            await message.channel.send(f"Unexpected error. Somehow, there is no room loaded. War stopped. Recommend the command: {server_prefix}reset")
            this_bot.setWar(None)
            return
    
    
        fc_tags = {}
        numGPS = this_bot.getWar().numberOfGPs
        players = list(this_bot.getRoom().getFCPlayerListStartEnd(1, numGPS*4).items())
        player_fcs_tags, hasANoneTag = getTagsSmart(players, this_bot.getWar().playersPerTeam)
        if hasANoneTag:
            player_fcs_tags = {}
            for fc_player in players:
                player_fcs_tags[fc_player] = getTagSmart(fc_player[1])
        player_fcs_tags = sorted(player_fcs_tags.items(), key=lambda x: x[1])
                
        if len(players) != this_bot.getWar().get_num_players():
            await message.channel.send(f'''Respond "{server_prefix}no" when asked ***Is this correct?*** - the number of players in the room doesn't match your war format and teams. Trying to still start war, but teams will be incorrect.''')
        
        teamTag = None
        previous_tags = []
        tag_counter = 0
        for playerNum, ((fc, playerName), (_, playerTag)) in enumerate(player_fcs_tags):
            if len(playerTag) < 1:
                playerTag = str(playerNum+1)
            
            if (playerNum) % this_bot.getWar().playersPerTeam == 0:
                #Start a new team
                teamTag = playerTag
                if teamTag in previous_tags:
                    tag_counter += 1
                    teamTag = f"{teamTag}_{tag_counter}"
                else:
                    tag_counter = 0
                previous_tags.append(teamTag)
            fc_tags[fc] = teamTag
            
        this_bot.getWar().setTeams(fc_tags)
        started_war_str = "Started war."
        if this_bot.getWar().ignoreLargeTimes:
            started_war_str += " (Ignoring errors for large finish times)"
        started_war_str += " rxx: "
        if len(this_bot.getRoom().rLIDs) == 1:
            started_war_str += str(this_bot.getRoom().rLIDs[0])
        else:
            started_war_str += str(this_bot.getRoom().rLIDs)
        await message.channel.send(started_war_str)

    @staticmethod                  
    async def merge_room_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return                  
    
        await message.channel.send("Feature under development. Please use with extreme caution.")
        if len(args) < 2:
            await message.channel.send("Nothing given to mergeroom. No merges nor changes made.") 
            return
        if _is_rLID(args[1]) and args[0] in this_bot.getRoom().rLIDs:
            await message.channel.send("The rLID you gave is already merged for this room. You can't merge a room with itself.") 
            return
    
        roomLink, rLID, rLIDSoup = await WiimfiSiteFunctions.getRoomDataSmart(args[1])
        rLIDSoupWasNone = rLIDSoup is None
        if not rLIDSoupWasNone:
            rLIDSoup.decompose()
            del rLIDSoup
            
        if roomLink is None or rLID is None or rLIDSoupWasNone:
            await message.channel.send("Either the FC given to mergeroom isn't in a room, or the rLID given to mergeroom doesn't exist. No merges nor changes made. **Make sure the new room has finished the first race before using this command.**") 
            return
        
        if rLID in this_bot.getRoom().rLIDs:
            await message.channel.send("The room you are currently in has already been merge in this war. No changes made.")  
            return
    
        this_bot.add_save_state(message.content)
        this_bot.getRoom().rLIDs.insert(0, rLID)
        updated = await this_bot.update_room()
        if updated:
            await message.channel.send("Rooms successfully merge. Number of races played: " + str(len(this_bot.getRoom().races)))
        else:
            this_bot.setWar(None)
            this_bot.setRoom(None)
            await message.channel.send("**Failed to merge. War has been stopped and room has unloaded**") 
    
    @staticmethod
    async def table_theme_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        if len(args) == 1:
            await send_table_theme_list(message, args, this_bot, server_prefix, server_wide=False)
        
        if len(args) > 1:
            setting = args[1]
            if this_bot.is_valid_style(setting):
                this_bot.add_save_state(message.content)
                this_bot.set_style(setting)
                await message.channel.send(f"Table theme set to: **{this_bot.get_style_name()}**")
            else:
                await message.channel.send(f"That is not a valid table theme setting. To see valid settings, run the command `{server_prefix}{args[0]}` and read carefully.")
    
    
    @staticmethod
    async def table_graph_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        else:
            if len(args) == 1:
                await send_available_graph_list(message, args, this_bot, server_prefix, server_wide=False)
            elif len(args) > 1:
                setting = args[1]
                if this_bot.is_valid_graph(setting):
                    this_bot.add_save_state(message.content)
                    this_bot.set_graph(setting)
                    await message.channel.send(f"Table graph set to: **{this_bot.get_graph_name()}**")
                else:
                    await message.channel.send(f"That is not a valid graph setting. To see valid settings, run the command `{server_prefix}{args[0]}` and read carefully.")
             
    @staticmethod           
    async def all_players_command(message:discord.Message, this_bot:ChannelBot, server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        players = list(this_bot.getRoom().getFCPlayerListStartEnd(1, len(this_bot.getRoom().races)).items())
        FC_List = [fc for fc, _ in players]
        await updateData(* await LoungeAPIFunctions.getByFCs(FC_List))
        await message.channel.send(this_bot.getRoom().get_players_list_string())
    
    @staticmethod
    async def set_war_name_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool, old_command:str):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        elif len(args) < 2:
            await message.channel.send("No war name given. War name not set.") 
        else:
            this_bot.add_save_state(message.content)
            this_bot.getWar().setWarName(old_command[len(server_prefix)+len("setwarname"):].strip())
            await message.channel.send("War name set!")  
            
    @staticmethod
    async def undo_command(message:discord.Message, this_bot:ChannelBot, server_prefix:str, is_lounge_server:bool):   
        if not this_bot.table_is_set() or not this_bot.getRoom().is_initialized():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        undone_command = this_bot.restore_last_save_state()
        if undone_command is False:
            await message.channel.send("There is nothing to undo.")
            return
        
        await message.channel.send(f"The following command has been undone: {UtilityFunctions.process_name(undone_command)}\nRun {server_prefix}wp to make sure table bot is fully refreshed.")
    
    @staticmethod
    async def early_dc_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool): 
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        if len(args) == 1:
            await message.channel.send("Specify a GP Number. Do: " + server_prefix + 'earlydc <gpNumber>')
            return    
    
        roomSize = None
        if not args[1].isnumeric():
            await message.channel.send("gpNumber must be a number. Do: " + server_prefix + 'earlydc <gpNumber>')
            return
    
        gpNum = int(args[1])
        raceNum = (gpNum * 4) - 3
        if raceNum < 1 or raceNum > len(this_bot.getRoom().races):
            await message.channel.send("The room hasn't started GP" + str(gpNum) + " yet.")
            return
    
        if len(args) >= 3:
            if args[2] == 'before' or args[2] == 'notonresults':
                roomSize = this_bot.getRoom().races[raceNum-1].getNumberOfPlayers()
        
        if roomSize is None:
            roomSize = this_bot.getWar().get_num_players()
        
        this_bot.add_save_state(message.content)
        this_bot.getRoom().forceRoomSize(raceNum, roomSize)
        await message.channel.send("Changed room size to " + str(roomSize) + " players for race #" + str(raceNum) + ".")      
    
    @staticmethod
    async def change_room_size_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
    
        if len(args) < 3:
            await message.channel.send("Specify a race number. Do: " + server_prefix + 'changeroomsize <racenumber> <roomsize>')      
            return
    
        if not args[1].isnumeric():
            await message.channel.send("racenumber must be a number. Do: " + server_prefix + 'changeroomsize <racenumber> <roomsize>')      
            return
        if not args[2].isnumeric():
            await message.channel.send("roomsize must be a number. Do: " + server_prefix + 'changeroomsize <racenumber> <roomsize>')      
            return
        
        raceNum = int(args[1])
        roomSize = int(args[2])
        if raceNum < 1 or raceNum > len(this_bot.getRoom().races):
            await message.channel.send("The room hasn't played race #" + str(raceNum) + " yet.")      
        elif roomSize < 2 or roomSize > 12:
            await message.channel.send("Room size must be between 2 and 12 players. (24P support may come eventually).")      
        else:
            this_bot.add_save_state(message.content)
            this_bot.getRoom().forceRoomSize(raceNum, roomSize)
            await message.channel.send("Changed room size to " + str(roomSize) + " players for race #" + str(raceNum) + ".")      
    
    @staticmethod
    async def race_results_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        else: 
            await updateData(* await LoungeAPIFunctions.getByFCs(this_bot.getRoom().getFCs()))
            if len(args) == 1:
                await message.channel.send(str(this_bot.getRoom().races[-1]))
            else:
                if args[1].isnumeric():
                    raceNum = int(args[1])
                    if raceNum < 1 or raceNum > len(this_bot.getRoom().races):
                        await message.channel.send("You haven't played that many races yet!")
                    else:
                        await message.channel.send(str(this_bot.getRoom().races[raceNum-1]))
                else:
                    await message.channel.send("That's not a race number!")
                    
    @staticmethod
    async def war_picture_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        server_id = message.guild.id
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)                   
        else:
            populate_mii_task = asyncio.get_event_loop().create_task(this_bot.populate_miis(str(message.id)))
        
            should_send_notification = this_bot.shouldSendNoticiation()
            wpCooldown = this_bot.getWPCooldownSeconds()
            if wpCooldown > 0:
                delete_me = await message.channel.send("Wait " + str(wpCooldown) + " more seconds before using this command.")
                await delete_me.delete(delay=5)
            else:
                
                this_bot.updateWPCoolDown()
                message2 = await message.channel.send("Updating room...")
                players = list(this_bot.getRoom().getFCPlayerListStartEnd(1, this_bot.getWar().numberOfGPs*4).items())
                FC_List = [fc for fc, _ in players]
                
                await updateData(* await LoungeAPIFunctions.getByFCs(FC_List))
                
                updated = await this_bot.update_room()
                if not updated:
                    await message2.edit(content="Room not updated. Please do " + server_prefix + "sw to load a different room.")
                else:
                    await message2.edit(content=str("Room updated. Room has finished " + \
                                                    str(len(this_bot.getRoom().getRaces())) +\
                                                    " races. Last race: " +\
                                                    str(this_bot.getRoom().races[-1].getTrackNameWithoutAuthor())))
                    message3 = await message.channel.send("Getting table...")
                    usemiis, miiArgRequested, _ = getUseMiis(args)
                    uselounge, loungeArgRequested = getUseLoungeNames(args)
                    if miiArgRequested and not loungeArgRequested:
                        uselounge = not usemiis
                    if loungeArgRequested and not miiArgRequested:
                        usemiis = not uselounge
                    use_lounge_otherwise_mii = False
                    
                    if not miiArgRequested and not loungeArgRequested:
                        use_lounge_otherwise_mii = True
                    
                    
                    lounge_replace = False
                    if uselounge:
                        lounge_replace = True
                    
                    step = this_bot.get_race_size()
                    if len(args) > 1 and args[1] in {'byrace', 'race'}:
                        step = 1
                    table_text, table_sorted_data = SK.get_war_table_DCS(this_bot, use_lounge_otherwise_mii=use_lounge_otherwise_mii, use_miis=usemiis, lounge_replace=lounge_replace, server_id=server_id, step=step)
                    table_text_with_style_and_graph = table_text + this_bot.get_lorenzi_style_and_graph(prepend_newline=True)
                    display_url_table_text = urllib.parse.quote(table_text)
                    true_url_table_text = urllib.parse.quote(table_text_with_style_and_graph)
                    image_url = common.base_url_lorenzi + true_url_table_text
                    
                    table_image_path = str(message.id) + ".png"
                    image_download_success = await common.download_image(image_url, table_image_path)
                    try:
                        if not image_download_success:
                            await message.channel.send("Could not download table picture.")
                            await populate_mii_task
                            return
                        #did the room have *any* errors? Regardless of ignoring any type of error
                        war_had_errors = len(this_bot.getWar().get_all_war_errors_players(this_bot.getRoom(), False)) > 0
                        tableWasEdited = len(this_bot.getWar().manualEdits) > 0 or len(this_bot.getRoom().dc_on_or_before) > 0 or len(this_bot.getRoom().forcedRoomSize) > 0 or this_bot.getRoom().had_positions_changed() or len(this_bot.getRoom().get_removed_races_string()) > 0
                        header_combine_success = ImageCombine.add_autotable_header(errors=war_had_errors, table_image_path=table_image_path, out_image_path=table_image_path, edits=tableWasEdited)
                        footer_combine_success = True
            
                        if header_combine_success and this_bot.getWar().displayMiis:
                            footer_combine_success = ImageCombine.add_miis_to_table(this_bot, table_sorted_data, table_image_path=table_image_path, out_image_path=table_image_path)
                        if not header_combine_success or not footer_combine_success:
                            await message3.delete() 
                            await message.channel.send("Internal server error when combining images. Sorry, please notify BadWolf immediately.")  
                        else:
                            embed = discord.Embed(
                                title = "",
                                description="[Edit this table on Lorenzi's website](" + common.base_url_edit_table_lorenzi + display_url_table_text + ")",
                                colour = discord.Colour.dark_blue()
                            )
                            
                            file = discord.File(table_image_path, filename=table_image_path)
                            numRaces = 0
                            if this_bot.getRoom() is not None and this_bot.getRoom().races is not None:
                                numRaces = min( (len(this_bot.getRoom().races), this_bot.getRoom().getNumberOfGPS()*4) )
                            embed.set_author(name=this_bot.getWar().getWarName(numRaces), icon_url="https://64.media.tumblr.com/b0df9696b2c8388dba41ad9724db69a4/tumblr_mh1nebDwp31rsjd4ho1_500.jpg")
                            embed.set_image(url="attachment://" + table_image_path)
                            
                            temp = this_bot.getWar().get_war_errors_string_2(this_bot.getRoom(), lounge_replace)
                            error_message = "\n\nMore errors occurred. Embed only allows so many errors to display."
                            if len(temp) + len(error_message) >= 2048:
                                temp = temp[:2048-len(error_message)] + error_message
                            embed.set_footer(text=temp)
                            await message.channel.send(file=file, embed=embed)
                            await message3.delete()
                            if should_send_notification and common.current_notification != "":
                                await message.channel.send(common.current_notification.replace("{SERVER_PREFIX}", server_prefix))
                    finally:
                        if os.path.exists(table_image_path):
                            os.remove(table_image_path)
            await populate_mii_task
    
    @staticmethod
    async def table_text_command(message:discord.Message, this_bot:ChannelBot, server_prefix:str, is_lounge_server:bool):
        server_id = message.guild.id
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
        else:
            try:
                table_text, _ = SK.get_war_table_DCS(this_bot, use_lounge_otherwise_mii=True, use_miis=False, lounge_replace=True, server_id=server_id, discord_escape=True)
                await message.channel.send(table_text)
            except AttributeError:
                await message.channel.send("Table Bot has a bug, and this mkwx room triggered it. I cannot tally your scores.")
                await message.channel.send("rLID is " + str(this_bot.getRoom().rLIDs) )
                raise        
            
    @staticmethod
    async def manual_war_setup(message:discord.Message, this_bot:ChannelBot, command:str):
        this_bot.manualWarSetUp = False
        
        if this_bot.getRoom() is None or not this_bot.getRoom().is_initialized():
            await message.channel.send("Unexpected error. Somehow, there is no room loaded. Recommend the command: reset")
            this_bot.setWar(None)
            return
    
        numGPS = this_bot.getWar().numberOfGPs
        
        players = list(this_bot.getRoom().getFCPlayerListStartEnd(1, numGPS*4).items())
        player_fcs_tags, hasANoneTag = getTagsSmart(players, this_bot.getWar().playersPerTeam)
        if hasANoneTag:
            player_fcs_tags = {}
            for fc_player in players:
                player_fcs_tags[fc_player] = getTagSmart(fc_player[1])
    
        #sort the fcs_tags by their tag
        player_fcs_tags = sorted(player_fcs_tags.items(), key=lambda x: x[1])
    
        fc_tag = {} #FC is the key, and tag is the value
        teamTag = None
        previous_tags = []
        tag_counter = 0
        for playerNum, ((fc, playerName), (_, playerTag)) in enumerate(player_fcs_tags):
            if len(playerTag) < 1:
                playerTag = str(playerNum+1)
            
            if (playerNum) % this_bot.getWar().playersPerTeam == 0:
                #Start a new team
                teamTag = playerTag
                if teamTag in previous_tags:
                    tag_counter += 1
                    teamTag = f"{teamTag}_{tag_counter}"
                else:
                    tag_counter = 0
                previous_tags.append(teamTag)
            fc_tag[fc] = teamTag
    
    
        teamBlob = command.split("/")
        
        
        for team in teamBlob:
            teamArgs = team.split()
            if len(teamArgs) < 2:
                await message.channel.send("Each team should have at least 1 player...")
                this_bot.setWar(None)
                return
            
            teamTag = teamArgs[0]
            for pos in teamArgs[1:]:
                if not pos.isnumeric():
                    processed_team_name = UtilityFunctions.process_name(str(teamTag))
                    userinput_team_position = UtilityFunctions.process_name(str(pos))
                    await message.channel.send(f"On team {processed_team_name}, {userinput_team_position} isn't a number. War stopped.")
                    this_bot.setWar(None)
                    return
                if int(pos) <= len(player_fcs_tags) and int(pos) >= 1:
                    fc_tag[player_fcs_tags[int(pos)-1][0][0]] = teamTag
             
                
        else:
            this_bot.getWar().setTeams(fc_tag)
            started_war_str = "Started war."
            if this_bot.getWar().ignoreLargeTimes:
                started_war_str += " (Ignoring errors for large finish times)"
                
            started_war_str += " rxx: "
            if len(this_bot.getRoom().rLIDs) == 1:
                started_war_str += str(this_bot.getRoom().rLIDs[0])
            else:
                started_war_str += str(this_bot.getRoom().rLIDs)
            await message.channel.send(started_war_str)
    
    @staticmethod
    async def remove_race_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        if len(args) == 1:
            await message.channel.send("Here's how to do this command: " + server_prefix + "removerace <raceNumber>\nYou can do **" + server_prefix + "races** to see the races you've played.")
            return
        
        if not args[1].isnumeric():
            await message.channel.send("That's not a race number!")  
            return
            
        raceNum = int(args[1])
        if raceNum < 1 or raceNum > len(this_bot.getRoom().races):
            await message.channel.send("You haven't played that many races yet!")
            return
    
        await message.channel.send("Feature under development. Please use with caution as it may have unintended side effects on your table.")
        command, save_state = this_bot.get_save_state(message.content)
        success, removed_race = this_bot.getRoom().remove_race(raceNum-1)
        if not success:
            await message.channel.send("Removing this race failed. (I did say it was under development!)")
        else:
            this_bot.add_save_state(command, save_state)
            await message.channel.send(f"Removed race #{removed_race[0]+1}: {removed_race[1]}")
    
    @staticmethod     
    async def gp_display_size_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
            return
    
        if len(args) != 2:
            await message.channel.send(f"The syntax of this command is `{server_prefix}{args[0]} <displaySize>`")
            return
        
        new_size = args[1]
        if not new_size.isnumeric():
            await message.channel.send(f"displaySize must be a number. For example, `{server_prefix}{args[0]} 1`")
            return
        
        new_size = int(new_size)
        if new_size < 1 or new_size > 32:
            await message.channel.send(f"displaySize must be between 1 and 32. For example, `{server_prefix}{args[0]} 1`")
        else:
            this_bot.add_save_state(message.content)
            this_bot.set_race_size(new_size)
            await message.channel.send(f"Each section of the table will now be {new_size} races.")
    
    @staticmethod
    async def quick_edit_command(message:discord.Message, this_bot:ChannelBot, args:List[str], server_prefix:str, is_lounge_server:bool, command:str):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server)
        else:
            if len(args) == 1:
                to_send = this_bot.getRoom().get_sorted_player_list_string()
                to_send += "\n**To change the placement of the 8th player on the list for the 7th race to 4th place, do:** *" + server_prefix + "quickedit 8 7 4*"
                await message.channel.send(to_send)
            elif len(args) == 4:
                playerNum = command.split()[1].strip()
                raceNum = args[2]
                placement = args[3]
                players = this_bot.getRoom().get_sorted_player_list()
                
                if not raceNum.isnumeric():
                    await message.channel.send("The race number must be a number.")
                elif not placement.isnumeric():
                    await message.channel.send("The placement number must be a number.")
                else:
                    
                    if not playerNum.isnumeric():
                        lounge_name = str(copy.copy(playerNum))
                        loungeNameFCs = UserDataProcessing.getFCsByLoungeName(lounge_name)
                        for _playerNum, (fc, _) in enumerate(players, 1):
                            if fc in loungeNameFCs:
                                break
                        else:
                            _playerNum = None
                            
                            
                        if _playerNum is None:
                            await message.channel.send("Could not find Lounge name " + UtilityFunctions.process_name(str(lounge_name)) + " in this room.")
                        playerNum = _playerNum
                    else:
                        playerNum = int(playerNum)
                    if playerNum is not None:
                        raceNum = int(raceNum)
                        placement = int(placement)
                        if playerNum < 1 or playerNum > len(players):
                            await message.channel.send("The player number must be on this list (between 1 and " + str(len(players)) + ").")
                        elif raceNum < 1 or raceNum > len(this_bot.getRoom().races):
                            await message.channel.send("The room hasn't played race #" + str(raceNum))
                        elif placement < 1 or placement > len(this_bot.getRoom().races[raceNum-1].placements):
                            await message.channel.send("Race #" + str(raceNum) + " only has " + str(len(this_bot.getRoom().races[raceNum-1].placements)) + "racers, cannot change their place.")
                        else:
                            playerFC = players[playerNum-1][0]
                            if this_bot.getRoom().races[raceNum-1].FCInPlacements(playerFC):
                                this_bot.add_save_state(message.content)
                                this_bot.getRoom().races[raceNum-1].changePlacement(playerFC, placement)
                                await message.channel.send("Changed " + UtilityFunctions.process_name(players[playerNum-1][1] + lounge_add(players[playerNum-1][0]) + " place to " + str(placement) + " for race #" + str(raceNum) + "."))
                            else:
                                await message.channel.send(UtilityFunctions.process_name(players[playerNum-1][1] + lounge_add(players[playerNum-1][0]) + " is not in race #" + str(raceNum)))           
                                
            else:
                await message.channel.send("Do " + server_prefix + "quickedit to learn how to use this command.")        
    
    @staticmethod
    async def current_room_command(message:discord.Message, this_bot:ChannelBot, server_prefix:str, is_lounge_server:bool):
        if not this_bot.table_is_set():
            await sendRoomWarNotLoaded(message, server_prefix, is_lounge_server) 
        elif len(this_bot.getRoom().races) >= 1:
            await updateData(* await LoungeAPIFunctions.getByFCs(this_bot.getRoom().getFCs()))
            await message.channel.send(this_bot.getRoom().races[-1].getPlayersByPlaceInRoomString())





#============== Helper functions ================
valid_gp_flags = ["gp=", "gps=", "setgps="]
def getNumGPs(args, defaultGPs=3):
    if len(args) < 4:
        return -1, defaultGPs
    
    for valid_flag in valid_gp_flags:
        for index, arg in enumerate(args[3:], 3):
            temp_arg = arg.lower().strip()
            if len(temp_arg) > len(valid_flag) and temp_arg.startswith(valid_flag):
                numGPs = temp_arg[len(valid_flag):]
                if numGPs.isnumeric():
                    numGPs = int(numGPs)
                    if numGPs < 1:
                        return index, 1
                    elif numGPs > 15:
                        return index, 15
                    else:
                        return index, numGPs
    return -1, defaultGPs

valid_suppress_large_time_flags = ["largetime=off", "largetime=no","largetimes=off", "largetimes=no", "sui=yes","sui=on","sui=true", "lgt=no", "lgt=off", "psb=yes", "psb=on", "psb=true", "professionalseriesbagging=yes", "professionalseriesbagging=true"]
valid_unsuppress_large_time_flags = ["largetime=yes", "largetime=yes","largetimes=on", "largetimes=yes", "sui=no","sui=off","sui=false", "lgt=yes", "lgt=on", "psb=no", "psb=off", "psb=false", "professionalseriesbagging=no", "professionalseriesbagging=false"]
def getSuppressLargeTimes(args, default_use=False):
    if len(args) < 4:
        return -1, default_use
    
    for index, arg in enumerate(args[3:], 3):
        if arg.lower().strip() in valid_suppress_large_time_flags:
            return index, True
        if arg.lower().strip() in valid_unsuppress_large_time_flags:
            return index, False

    return -1, default_use


valid_mii_flags = ["usemiis=", "usemii=", "miis=", "miinames=", "mii=", "miiname=", 'miiheads=']
def getUseMiis(args, default_use=False, default_start_arg=1):
    if len(args) < 2:
        return default_use, False, -1
        
    for valid_flag in valid_mii_flags:
        for ind, arg in enumerate(args[default_start_arg:], default_start_arg):
            temp_arg = arg.lower().strip()
            if len(temp_arg) > len(valid_flag) and temp_arg.startswith(valid_flag):
                use_miis_input = temp_arg[len(valid_flag):].strip()
                if use_miis_input in ["y", "yes", "t", "true", 'on']:
                    return True, True, ind
                elif use_miis_input in ["n", "no", "false", "f", 'off']:
                    return False, True, ind
                else:
                    return default_use, False, ind

    return default_use, False, -1

valid_use_lounge_name_flags = ["uselounges=", "uselounge=", "lounges=", "loungenames=", "lounge=", "loungename="]
def getUseLoungeNames(args, default_use=True):
    if len(args) < 2:
        return default_use, False
    
    for valid_flag in valid_use_lounge_name_flags:
        for arg in args[1:]:
            temp_arg = arg.lower().strip()
            if len(temp_arg) > len(valid_flag) and temp_arg.startswith(valid_flag):
                use_discords_input = temp_arg[len(valid_flag):].strip()
                if use_discords_input in ["y", "yes", "t", "true"]:
                    return True, True
                elif use_discords_input in ["n", "no", "false", "f"]:
                    return False, True
                else:
                    return default_use, False
    return default_use, False


async def send_table_theme_list(message:discord.Message, args:List[str], this_bot:TableBot.ChannelBot, server_prefix:str, server_wide=False):
    server_wide_or_table_str = "default theme used for tables in this server" if server_wide else 'theme for this table'
    to_send = f"To change the *{server_wide_or_table_str}*, choose a theme number from this list and do `{server_prefix}{args[0]} <themeNumber>`:\n"
    to_send += this_bot.get_style_list_text()
    return await message.channel.send(to_send)
        
async def send_available_graph_list(message:discord.Message, args:List[str], this_bot:TableBot.ChannelBot, server_prefix:str, server_wide=False):
    server_wide_or_table_str = "default graph used for tables in this server" if server_wide else 'graph for this table'
    to_send = f"To change the *{server_wide_or_table_str}*, choose a graph number from this list and do `{server_prefix}{args[0]} <graphNumber>`:\n"
    to_send += this_bot.get_graph_list_text()
    return await message.channel.send(to_send)

def get_mii_option(option_number) -> str:
    if option_number == "1" or option_number == 1:
        return "**Miis will be shown** at the bottom of the table by default for tables in this server."
    elif option_number == "2" or option_number == 2:
        return "**Miis will NOT be shown** at the bottom of the table by default for tables in this server."
    return "Unknown Option"

def get_large_time_option(option_number) -> str:
    if option_number == "1" or option_number == 1:
        return "**Show large times** by default for tables in this server."
    elif option_number == "2" or option_number == 2:
        return "**Hide large times** by default for tables in this server."
    return "Unknown Option"

async def send_available_mii_options(message:discord.Message, args:List[str], this_bot:TableBot.ChannelBot, server_prefix:str, server_wide=False):
    to_send = f"Choose an option from this list and do `{server_prefix}{args[0]} <optionNumber>`:\n"
    to_send += f"""`1.` {get_mii_option(1)}
`2.` {get_mii_option(2)}"""
    return await message.channel.send(to_send)

async def send_available_large_time_options(message:discord.Message, args:List[str], this_bot:TableBot.ChannelBot, server_prefix:str, server_wide=False):
    to_send = f"Choose an option from this list and do `{server_prefix}{args[0]} <optionNumber>`:\n"
    to_send += f"""`1.` {get_large_time_option(1)}
`2.` {get_large_time_option(2)}"""
    return await message.channel.send(to_send)


def dump_vr_is_on():
    with open(common.VR_IS_ON_FILE, "wb") as pickle_out:
        try:
            pkl.dump(vr_is_on, pickle_out)
        except:
            print("Could not dump pickle for vr_is_on. Current state:", vr_is_on)
            
def load_vr_is_on():
    global vr_is_on
    if os.path.exists(common.VR_IS_ON_FILE):
        with open(common.VR_IS_ON_FILE, "rb") as pickle_in:
            try:
                vr_is_on = pkl.load(pickle_in)
            except:
                print(f"Could not read in '{common.VR_IS_ON_FILE}'")
                
def example_help(server_prefix:str, original_command:str):
    return f"Do {server_prefix}{original_command} for an example on how to use this command."
                