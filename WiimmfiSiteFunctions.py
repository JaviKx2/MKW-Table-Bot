'''
Created on Jul 30, 2020

@author: willg
'''
from bs4 import BeautifulSoup, NavigableString
import re
from datetime import datetime, timedelta
import UserDataProcessing
import aiohttp
import codecs
import asyncio
import TableBotExceptions
import common
import UtilityFunctions
USING_EXPERIMENTAL_REQUEST = False
if USING_EXPERIMENTAL_REQUEST:
    #from concurrent.futures.process import ProcessPoolExecutor
    #from concurrent.futures.thread import ThreadPoolExecutor
    #Number of minutes between captchas
    captcha_time_estimation = 117
    import undetected_chromedriver.v2 as uc
    #from selenium import webdriver as uc
    options = uc.ChromeOptions()
    options.add_extension('./anticaptcha-plugin_v0.59.crx')
    #options.add_extension('./plugin.zip')
    number_of_browsers = 1
    driver_infos = [[uc.Chrome("./chrome-cli/chromedriver.exe", options=options), 0, 0, 0, False] for _ in range(number_of_browsers)] #browser, number of cloudflare failures, number of ongoing requests, total requests, browser in use
    failures_allowed = 20
    #process_pool_executor = ThreadPoolExecutor(max_workers=number_of_browsers)
    
url_response_cache = {}
cache_time = timedelta(seconds=30)
long_cache_time = timedelta(seconds=45)
cache_size = 5
cache_deletion_time_limit = timedelta(hours=2)
lockout_timelimit = timedelta(minutes=5)







wiimmfi_url = 'https://wiimmfi.de'
mkwxURL = 'https://wiimmfi.de/stats/mkwx'
if "mkwx_proxy_url" in common.properties:
    mkwxURL = common.properties['mkwx_proxy_url']
submkwxURL = f"{mkwxURL}/list/"
special_test_cases = {
f"{submkwxURL}r0000000":("Special room: Room has times with high deltas and a race with times that are the same as another race's times", f"{common.SAVED_ROOMS_DIR}SameTimeHighDelta.html"),
f"{submkwxURL}r0000001":("Table Bot Challenge Room One", f"{common.SAVED_ROOMS_DIR}TableBotTestOne.html"),
f"{submkwxURL}r0000002":("Table Bot Challenge Room Two", f"{common.SAVED_ROOMS_DIR}TableBotTestTwo.html"),
f"{submkwxURL}r0000003":("Table Bot Remove Race Test w/ quickedit", f"{common.SAVED_ROOMS_DIR}removerace_one.html"),
f"{submkwxURL}r0000004":("Table Bot Remove Race Test w/ quickedit, 2nd room to merge", f"{common.SAVED_ROOMS_DIR}removerace_two.html"),
f"{submkwxURL}r0000005":("Clean room with no errors.", f"{common.SAVED_ROOMS_DIR}clean_room.html"),
f"{submkwxURL}r0000006":("Tag in brackets.", f"{common.SAVED_ROOMS_DIR}tag_in_brackets.html"),
f"{submkwxURL}r0000007":("Room with an unknown track name (SHA name).", f"{common.SAVED_ROOMS_DIR}unknown_track.html"),
f"{submkwxURL}r0000008":("Room with email protected tags", f"{common.SAVED_ROOMS_DIR}email_protected.html")
}





def select_free_driver():
    index_of_min_driver = 0
    cur_min = (driver_infos[0][2], driver_infos[0][3])
    for ind, driver_info in enumerate(driver_infos):
        if (driver_info[2], driver_info[3]) < cur_min and not driver_info[4]: #If the load for the driver is the lowest AND it is not in use...
            index_of_min_driver = ind
            cur_min = (driver_info[2], driver_info[3])
    return index_of_min_driver, driver_infos[index_of_min_driver]

SAFE_DRIVER_RESTART_TIMEOUT = 45
async def safe_restart_driver(index, logging_message):
    for _ in range(SAFE_DRIVER_RESTART_TIMEOUT):
        if driver_infos[index][4]:
            await asyncio.sleep(1)
        if not driver_infos[index][4]:
            await restart_driver(index, logging_message)
            return True
    return False

#Note: We don't reset the total number of requests. The total number of requests accumulates regardless of if the browser is restarted
#This is to ensure that, assuming the load is equal (eg the number of requests in the queue for a browser) across all 3 browsers, the browser selection continues to rotate
async def restart_driver(index, logging_message):
    driver_info = driver_infos[index]
    driver_info[4] = True
    print(logging_message)
    driver_info[1] = 0
    driver_info[0].quit()
    await asyncio.sleep(3)
    driver_info[0] = uc.Chrome("./chrome-cli/chromedriver.exe", options=options)
    await asyncio.sleep(3)
    driver_info[2] = 0
    driver_info[4] = False

async def cloudflare_block_handle(driver_index, original_source):
    originally_had_cloudflare = False
    if "Ray ID: " in original_source:
        print("Blocked by Cloudflare, attempting first bypass")
        originally_had_cloudflare = True
        await asyncio.sleep(5)
        
        if "Ray ID: " in driver_infos[driver_index][0].page_source:
            print("Blocked by Cloudflare, attempting second bypass through restart...")
            driver_infos[driver_index][0].service.stop()
            await asyncio.sleep(6)
            driver_infos[driver_index][0].service.start()
            driver_infos[driver_index][0].start_session()
            await asyncio.sleep(2)
    return originally_had_cloudflare, "Ray ID: " not in driver_infos[driver_index][0].page_source



def print_url_cache():
    for url, url_cache_info in url_response_cache.items():
        print(f"{url}: {url_cache_info[0]} - {url_cache_info[1]}:")
        for page_cache in url_cache_info[2]:
            print(f"{page_cache[0]}: {page_cache[1][:20]}")
            
def cache_time_expired(last_access_time, current_time, cache_time=cache_time):
    return (current_time - last_access_time) > cache_time

#Redundancy check
def free_locked_pages():
    current_time = datetime.now()
    try: #Need to try because clear_old_cache can cause a race condition
        for cache_info in url_response_cache.values():
            if cache_info[0]: #currently "pulling" - either locked, or actually true
                
                #If it's been unreasonably long, it's safe to assume we someone got locked
                #This isn't actually guaranteed, BUT....
                #...we're not implementing a fully safe multi-thread caching mechanism, because the entire point of this is to minimize mkwx requests
                #If the absurd scenario a request did somehow did take 60 seconds and we get caught in a microsecond timeperiod race and we send two requests to the URL,
                #OH WELL. THAT'S LIFE.
                if cache_time_expired(cache_info[1], current_time, lockout_timelimit): 
                    cache_info[0] = False #Set flag to not pulling anymore, so it's unlocked and can be pulled again
    except:
        #Off the top of my head, an iteration change exception could occur. More might, but they generally all mean that we failed. We'll just try again later.
        print(f"Race condition happened in free_locked_pages")
        pass
        
def clear_old_caches():
    current_time = datetime.now()
    urls_to_delete = set()
    try: #Need to try because clear_old_cache itself can cause a race condition
        for url, (currently_pulling, last_pull_entry_time, page_caches) in url_response_cache.items():
            if cache_time_expired(last_pull_entry_time, current_time, cache_deletion_time_limit):
                urls_to_delete.add(url)
            
            while len(page_caches) >= 5:
                try: #Race condition avoidance: just because we were told there were enough pages in the previous line doesn't mean that there will be on the next line
                    del page_caches[0]
                except:
                    print(f"Race condition happened, pages weren't removed from this url's cache: {url}")
                    break
                
                
        for url in urls_to_delete:
            try: #trying because race condition might exist - just because url was in the url_response_cache a few lines ago doesn't mean it still is, or that it's delete-able
                del url_response_cache[url]
            except:
                print(f"Race condition happened, url wasn't deleted from cache: {url}")
    except:
        #Off the top of my head, an iteration change exception could occur. More might, but they generally all mean that we failed. We'll just try again later.
        print(f"Race condition happened in clear_old_caches")

async def cloudflare_failure_check():
    for index, driver_info in enumerate(driver_infos):
        if driver_info[1] >= failures_allowed and not driver_info[4]:
            await restart_driver(index, logging_message=f"Driver at {index} had {driver_info[1]} failures and {driver_info[2]} ongoing requests. Restarting browser...")


#async def delay_until_url_matches(driver, url, timeout=timedelta(seconds=10)):
#    pass

async def threaded_fetch(session, url, use_long_cache_time=False):
    if USING_EXPERIMENTAL_REQUEST:
        #result = await asyncio.get_event_loop().run_in_executor(process_pool_executor, fetch, session, url, use_long_cache_time)
        result = None
        return result
    else:
        return await __fetch__(session, url, use_long_cache_time)
        
          
#def fetch(session, url, use_long_cache_time=False):
#    return asyncio.run(__fetch__(session, url, use_long_cache_time))

async def __fetch__(session, url, use_long_cache_time=False):
    #print_url_cache()
    free_locked_pages()
    clear_old_caches()
    caching_time = long_cache_time if use_long_cache_time else cache_time
    #Wait until the url is finished pulling... poll 5 times...
    current_time = datetime.now()
    for _ in range(5):
        try: #Race condition avoidance: in the following line, it's possible that the url is in the cache for the first part of statement, but not the second part of the statement
            if url in url_response_cache and url_response_cache[url][0]: #check if url is being pulled
                await asyncio.sleep(2)
                if not (url in url_response_cache and url_response_cache[url][0]): #To catch the final try and avoid a huge time window which would certainly result in race conditions
                    break  
            else: #URL is either not in cache, or not trying to pull
                break
        except (AttributeError, IndexError):
            pass
            
    else: #We polled 5 times without breaking, which means a request took a long time. Shouldn't normally happen, but we'll return the most
        #recent soup if we have one, otherwise none
        _, last_access_time, page_caches = None, datetime.min, []
        try:
            _, last_access_time, page_caches = url_response_cache[url]
        except:
            raise TableBotExceptions.CacheRaceCondition("Failure in cache, race condition happened.")
        
        #At this point, we're promised that the url cache information (last_access_time, page_caches) is from the cache dict
        if len(page_caches) > 0:
            try:
                most_recent_update, page_cache = page_caches[-1]
                print(f"{current_time.time()}: fetch({url}) hit the cache because page was being pulled, but didn't finish in 5 seconds. (Page was downloaded {(current_time - most_recent_update).total_seconds()} seconds ago, and fetching the page was locked at {last_access_time.time()}, which was {(current_time - last_access_time).total_seconds()} seconds ago.)")
                return page_cache
            except:
                raise TableBotExceptions.CacheRaceCondition("Failure in cache, race condition happened.")
    
        #else: which means that page cache was empty
        if not cache_time_expired(last_access_time, current_time, caching_time):
            raise TableBotExceptions.RequestedRecently("URL Requested recently, but didn't have a cache. (This means that the original request was unsuccessful, but we don't want to hit the website again.)")

        raise TableBotExceptions.URLLocked("URL is locked")
                
    to_return = None
    cloudflare_failure = False
    all_browsers_busy = False
    try: #Very important, if we throw an exception without setting our flag to False, the URL will become permanently inaccessible
        if url not in url_response_cache:
            #print(f"{url} wasn't in url_response_cache: {len(url_response_cache)}")
            url_response_cache[url] = [True, current_time, []]
            
        url_cache_info = url_response_cache[url]
            
        recent_pulls_for_url = url_cache_info[2]
        if len(recent_pulls_for_url) > 0:
            last_updated = recent_pulls_for_url[-1][0]
            if not cache_time_expired(last_updated, current_time, caching_time): #If we haven't waited long enough... hit the cache
                print(f"{current_time.time()}: fetch({url}) hit the cache because page was downloaded {(current_time - last_updated).total_seconds()} seconds ago.")
                to_return = recent_pulls_for_url[-1][1]
        
        
        if to_return is None: #At this point, we know the page isn't in the cache, or it is super outdated
            #set the flag to currently pulling, and update the pulling time to now
            url_response_cache[url][0] = True
            url_response_cache[url][1] = current_time
            if not USING_EXPERIMENTAL_REQUEST:
                print(f"{current_time.time()}: fetch({url}) is making an HTTPS request.")
                async with session.get(url, ssl=common.sslcontext) as response:
                    to_return = await response.text()
                    recent_pulls_for_url.append([current_time, to_return])
            else:
                await cloudflare_failure_check()
                driver_index, driver_info = select_free_driver()
                for _ in range(10):
                    if driver_info[4]: #if driver is busy...
                        await asyncio.sleep(1) #wait a second, then find a new one
                        driver_index, driver_info = select_free_driver() #Try to pick a new driver
                    else:
                        break
                else:
                    all_browsers_busy = True
                    raise TableBotExceptions.NoAvailableBrowsers("All browsers are busy.")
                
                driver_info[4] = True #set flag for currently pulling/busy (block adding requests)
                driver_info[2] += 1 #add one to number of current ongoing requests
                driver_info[3] += 1 #add one to total requests sent
                print(f"{current_time.time()}: fetch({url}) is making an HTTPS request: Driver #{driver_index}, {driver_info[2]} ongoing requests (including this one).")
                try:
                    driver_info[0].get(url)
                    page_source = driver_info[0].page_source
                    originally_had_cloudflare, bypassed_cloudflare = await cloudflare_block_handle(driver_index, page_source)
                        
                    if not bypassed_cloudflare:
                        cloudflare_failure = True
                        driver_info[1] += 1
                        print(f"Full block by Cloudflare: Driver at index {driver_index} now has {driver_info[1]} total blocked requests, and processing {driver_info[2]} outgoing requests (including this one).")
                        raise TableBotExceptions.MKWXCloudflareBlock("Cloudflare blocked page.")
                    #print(driver_info[0].current_url)
                    #await delay_until_url_matches(driver_info[0], url)
                    to_return = driver_info[0].page_source if originally_had_cloudflare else page_source
                    recent_pulls_for_url.append([current_time, to_return])
                except:
                    driver_info[2] -= 1 #reduce number of current ongoing requests by one
                    driver_info[4] = False
                    raise
                driver_info[2] -= 1 #reduce number of current ongoing requests by one
                driver_info[4] = False
        else: #Putting here for clarification on control flow, see comment below
            pass #no need for an else statement, if we hit our cache, we'll execute the finally statement and return it
    except Exception as e:
        if not isinstance(e, TableBotExceptions.MKWXCloudflareBlock):
            print(f"Got exception: {e}")
            common.log_text(str(e), common.ERROR_LOGGING_TYPE)
        to_return = None
    finally:
        url_response_cache[url][0] = False #set the flag to no longer pulling so we don't get locked out
        if cloudflare_failure:
            raise TableBotExceptions.MKWXCloudflareBlock("Cloudflare blocked page.")
        if all_browsers_busy:
            raise TableBotExceptions.NoAvailableBrowsers("All browsers are busy.")
        if to_return is None:
            raise TableBotExceptions.WiimmfiSiteFailure("Could not pull information from mkwx.")
        return to_return

# https://github.com/jslirola/cloudflare-email-decoder/blob/master/ced/lib/processing.py
def decode_email(encodedString):
    r = int(encodedString[:2], 16)
    return ''.join([chr(int(encodedString[i:i + 2], 16) ^ r) for i in range(2, len(encodedString), 2)])


def replace_content(text):
    emailregex = 'data-cfemail=\"([^\"]+)\"'
    tagregex = r'<a [^>]*="\/cdn-cgi\/l\/email-protection"[^>]*>([^<]+)<\/a>'

    out = []
    for line in text.split("\n"):
        m = re.search(emailregex, line)
        if m:
            line = re.sub(tagregex, decode_email(m.group(1)), line)
        out.append(line)
    return "\n".join(out)

async def getRoomHTML(roomLink):
    
    if roomLink in special_test_cases:
        description, local_file_path = special_test_cases[roomLink]
        fp = codecs.open(local_file_path, "r", "utf-8")
        html_data = fp.read()
        fp.close()
        return replace_content(html_data)
        
    async with aiohttp.ClientSession() as session:
        temp = await threaded_fetch(session, roomLink, use_long_cache_time=True)
        return replace_content(temp)


async def __getMKWXSoupCall__():
    async with aiohttp.ClientSession() as session:
        mkwxHTML = await threaded_fetch(session, mkwxURL, use_long_cache_time=False)
        return BeautifulSoup(replace_content(mkwxHTML), "html.parser")

async def getMKWXSoup():
    if common.STUB_MKWX:
        fp = codecs.open(common.STUB_MKWX_FILE_NAME, "r", "utf-8")
        html_data = fp.read()
        fp.close()
        return BeautifulSoup(replace_content(html_data), "html.parser")
    return await __getMKWXSoupCall__()

async def getrLIDSoup(rLID):
    roomHTML = await getRoomHTML(submkwxURL + rLID)
    temp = BeautifulSoup(roomHTML, "html.parser")
    if temp.find(text="No match found!") is None:
        return temp
    return None
        


#getRoomLink old name
async def getRoomData(rid_or_rlid):
    if UtilityFunctions.is_rLID(rid_or_rlid): #It is a unique rxxxxxxx number given
        #Check if the rLID is a valid link (bogus input check, or the link may have expired)
        rLIDSoup = await getrLIDSoup(rid_or_rlid)
        if rLIDSoup is not None:
            return submkwxURL + rid_or_rlid, rid_or_rlid, rLIDSoup
        else:
            return None, None, None
        
    #Normal room ID given, go find the link for the list
    mkwxSoup = await getMKWXSoup()
        
    roomIDSpot = mkwxSoup.find(text=rid_or_rlid)
    if roomIDSpot is None:
        return None, None, None
    link = str(roomIDSpot.find_previous('a')[common.HREF_HTML_NAME])
    rLID = link.split("/")[-1]
    rLIDSoup = await getrLIDSoup(rLID)
    return wiimmfi_url + link, rLID, rLIDSoup #link example: /stats/mkwx/list/r1279851


#async def getAllSurfaceRoomData():
    

async def getMKWXHTMLDataByFC(fcs):
    soup = await getMKWXSoup()
    fcSpot = None
    for fc in fcs:
        fcSpot = soup.find(text=fc)
        if fcSpot is not None:
            break
        
    if fcSpot is None:
        return None
    #found the FC, now go get the room
    levels = [fcSpot.parent.parent.parent]
    del fcSpot
    #should run until we hit the roomID, but in cases of corrupt HTML, we don't want an infinite loop. So eventually, this will stop when there is no previous siblings
    returnNone = False
    while True:
        #print("\n\n=====================================================\n")
        
        levels.append(levels[-1].previous_sibling)
        #print(correctLevel)
        if levels[-1] is None:
            returnNone = True
            break
        if isinstance(levels[-1], NavigableString):
            continue
        if 'id' in levels[-1].attrs:
            break
    
    while len(levels) > 1:
        del levels[0]
        
    if returnNone:
        del levels[0]
        return None
    return levels.pop()



#getRoomLinkByFC old name
async def getRoomDataByFC(fcs):
    soup = await getMKWXSoup()
    fcSpot = None
    for fc in fcs:
        fcSpot = soup.find(text=fc)
        if fcSpot is not None:
            break
        
    if fcSpot is None:
        return None, None, None
    
    #found the FC, now go get the room
    correctLevel = fcSpot.parent.parent.parent
    #print(correctLevel)
    #should run until we hit the roomID, but in cases of corrupt HTML, we don't want an infinite loop. So eventually, this will stop when there is no previous siblings
    while True:
        #print("\n\n=====================================================\n")
        correctLevel = correctLevel.previous_sibling
        #print(correctLevel)
        if correctLevel is None:
            return None, None, None
        if isinstance(correctLevel, NavigableString):
            continue
        if 'id' in correctLevel.attrs:
            break
    link = correctLevel.find('a')[common.HREF_HTML_NAME]
    rLID = link.split("/")[-1]
    rLIDSoup = await getrLIDSoup(rLID)
    return wiimmfi_url + link, rLID, rLIDSoup #link example: /stats/mkwx/list/r1279851

#load_me can be an FC, roomID or rxxxxxx number, or discord name. Order of checking is the following: 
#Discord name, rxxxxxxx, FC, roomID
async def getRoomDataSmart(load_me):
    if not isinstance(load_me, list):
        load_me = load_me.strip().lower()
        if UtilityFunctions.is_rLID(load_me):
            return await getRoomData(load_me)
        
        if UtilityFunctions.is_fc(load_me):
            return await getRoomDataByFC([load_me])
        
        FCs = UserDataProcessing.getFCsByLoungeName(load_me)
        return await getRoomDataByFC(FCs)
        
    if isinstance(load_me, list):
        return await getRoomDataByFC(load_me)
    

async def getRoomHTMLDataSmart(load_me):
    if not isinstance(load_me, list):
        load_me = load_me.strip().lower()
        
        if UtilityFunctions.is_fc(load_me):
            return await getMKWXHTMLDataByFC([load_me])
        
        
        FCs = UserDataProcessing.getFCsByLoungeName(load_me)
        return await getMKWXHTMLDataByFC(FCs)
        
    if isinstance(load_me, list):
        return await getMKWXHTMLDataByFC(load_me)


#soups is a list of beautiful soup objects
def combineSoups(soups):
    last_soup = None
    for soup_num, soup in enumerate(soups):
        if soup_num == 0:
            last_soup = soup
        else:
            table_body = last_soup.find('table')
            table_body.append(soup.find('table'))
            
    while len(soups) > 0:
        del soups[0]
    
    return last_soup

