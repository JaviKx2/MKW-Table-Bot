BEGIN;
/*
RT_TABLE_BOT_CHANNEL_TIER_MAPPINGS = {
    843981870751678484:8,
    836652527432499260:7,
    747290199242965062:6,
    747290182096650332:5,
    873721400056238160:5,
    747290167391551509:4,
    801620685826818078:4,
    747290151016857622:3,
    801620818965954580:3,
    805860420224942080:3,
    747290132675166330:2,
    754104414335139940:2,
    801630085823725568:2,
    747289647003992078:1,
    747544598968270868:1,
    781249043623182406:1
    }

CT_TABLE_BOT_CHANNEL_TIER_MAPPINGS = {
    875532532383363072:7,
    850520560424714240:6,
    801625226064166922:5,
    747290436275535913:4,
    879429019546812466:4,
    747290415404810250:3,
    747290383297282156:2,
    823014979279519774:2,
    747290363433320539:1,
    871442059599429632:1
    }    
*/

/* Deletes all registered tiers */
DELETE FROM Tier;
			
/*Add channel_ids mapping to tiers*/			    
/* RT Table Bot Channels */
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(843981870751678484, 8, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(836652527432499260, 7, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290199242965062, 6, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290182096650332, 5, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(873721400056238160, 5, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290167391551509, 4, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(801620685826818078, 4, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290151016857622, 3, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(801620818965954580, 3, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(805860420224942080, 3, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290132675166330, 2, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(754104414335139940, 2, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(801630085823725568, 2, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747289647003992078, 1, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747544598968270868, 1, 0);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(781249043623182406, 1, 0);

/* CT Table Bot Channels */
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(875532532383363072, 7, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(850520560424714240, 6, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(801625226064166922, 5, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290436275535913, 4, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(879429019546812466, 4, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290415404810250, 3, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290383297282156, 2, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(823014979279519774, 2, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(747290363433320539, 1, 1);
INSERT INTO Tier (channel_id, tier, is_ct) VALUES(871442059599429632, 1, 1);

COMMIT;