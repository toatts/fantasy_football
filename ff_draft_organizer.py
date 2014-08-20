# HEADER ====================================================================================
# File   : ff_draft_organizer.py
# Author : Jay Oatts
# Email  : jay.oatts@gmail.com
# Date   : 8/18/2014
# Version: 0.4
# Summary:
# Scrapes projected consensus stats from http://www.fantasypros.com/nfl/projections for
# fantasy football. Compiles useful stats and applies league rules to get approximate
# season point total. Applies marginal value based on the article from
# http://www.thebiglead.com/index.php/2011/08/28/setting-auction-values-for-your-draft/
# Applies keeper league inflation based on http://espn.go.com/fantasy/football/story/_/
# page/NFLDK2K13_inflation_calculation/how-calculate-inflation-fantasy-football-auction-
# keeper-league
# Both sources should be available in same folder as this code.
# Output should be stored as a tab delimited text file to import into Excel for further
# manipulation on draft day. In addition to static inflation, dynamic inflation can be
# calculated with Excel by adjusting the marginal points per dollar as players are drafted.

# (C) Copyright 2014, All Rights Reserved


# IMPORTS ===================================================================================
import urllib.request
import math
import sys
import getopt
import os
import re
import config

from html.parser import HTMLParser

# GLOBALS ===================================================================================
# League Info
TOTAL_TEAMS      = config.teams
AUCTION_MONEY    = config.auction_money
ROSTER_SLOTS     = config.roster_slots
TOTAL_MONEY      = AUCTION_MONEY * TOTAL_TEAMS
DISCR_MONEY      = TOTAL_MONEY - (ROSTER_SLOTS * TOTAL_TEAMS)
# Scoring
PASS_CMP_PTS     = config.pass_completion
PASS_YRD_PTS     = config.passing_yard
PASS_TD_PTS      = config.passing_touchdown
INT_PTS          = config.interception
RUSH_ATT_PTS     = config.rushing_attempt
RUSH_YRD_PTS     = config.rushing_yard
RUSH_TD_PTS      = config.rushing_touchdown
FUMB_PTS         = config.fumble
RECEP_PTS        = config.reception
REC_YRD_PTS      = config.receiving_yard
REC_TD_PTS       = config.receiving_touchdown
# Keepers
KEEPER_SPENDINGS = config.keeper_money_used
KEEPER_VALUE     = config.keeper_value
KEEPER_INFLATION = (TOTAL_MONEY - KEEPER_SPENDINGS) / (TOTAL_MONEY - KEEPER_VALUE)
# Marginal Scoring
# ROSTER        = number of expected players drafted at that position (approximation)
# TOP_RESERVE   = number of starters at position * 1.5
# STARTER       = number of starters at position
# ELITE_STARTER = number of starters at position * 0.5
# NOTE: subtracted 1 for zero-based indexing
QB_ROSTER        = math.ceil(config.teams * config.expected_drafted_qbs) - 1
QB_TOP_RESERVE   = math.ceil(config.teams * config.starting_qbs * 1.5) - 1
QB_STARTER       = math.ceil(config.teams * config.starting_qbs) - 1
QB_ELITE_STARTER = math.ceil(config.teams * config.starting_qbs * 0.5) - 1
RB_ROSTER        = math.ceil(config.teams * config.expected_drafted_rbs - 1) - 1
RB_TOP_RESERVE   = math.ceil(config.teams * config.starting_rbs * 1.5) - 1
RB_STARTER       = math.ceil(config.teams * config.starting_rbs) - 1
RB_ELITE_STARTER = math.ceil(config.teams * config.starting_rbs * 0.5) - 1
WR_ROSTER        = math.ceil(config.teams * config.expected_drafted_wrs - 1) - 1
WR_TOP_RESERVE   = math.ceil(config.teams * config.starting_wrs * 1.5) - 1
WR_STARTER       = math.ceil(config.teams * config.starting_wrs) - 1
WR_ELITE_STARTER = math.ceil(config.teams * config.starting_wrs * 0.5) - 1
TE_ROSTER        = math.ceil(config.teams * config.expected_drafted_tes - 1) - 1
TE_TOP_RESERVE   = math.ceil(config.teams * config.starting_tes * 1.5) - 1
TE_STARTER       = math.ceil(config.teams * config.starting_tes) - 1
TE_ELITE_STARTER = math.ceil(config.teams * config.starting_tes * 0.5) - 1

# Program Settings
# 0 = none/little, 1 = chart displays, 2 = all (debug messaging)
VERBOSITY        = 1
OUT_FILE         = ''
HELP_MSG  = (
"Usage: python ff_draft_organizer.py <-opt setting>\n"
"-option      [description]\n"
"-h           [help file, prints out this message]\n"
"-v <0-2>     [verbosity, 0 = minimal, 1 = chart display (default), 2 = debug]\n"
"-o <file>    [output file, tab separated value type, if not specified then none created]\n"
)


# CLASSES ===================================================================================
class Projections_HTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self)
        self.expertsTable = False
        self.isExpert     = False
        self.expert       = []
        self.experts      = []

        self.startPlayer  = False
        self.statsTable   = False
        self.isName       = False
        self.isTeam       = False
        self.isStat       = False
        self.player       = []
        self.players      = []
        self.name         = ''
        self.team         = ''

    def handle_starttag(self, tag, attrs):
        # Catch expert table
        if (tag == "table"):
            for (attr, data) in attrs:
                if ((attr == "id") and (data == "experts")):
                    self.expertsTable = True
        # Catch expert data
        if (tag == "td") and (self.expertsTable):
            self.isExpert = True
        # Catch player table
        if (tag == "table"):
            for (attr, data) in attrs:
                if ((attr == "id") and (data == "data")):
                    self.statsTable = True
        # Catch player name
        if (tag == "a") and (self.statsTable):
            self.startPlayer = True
            self.isName = True
        # Catch player team (may not exist for all players)
        if (tag == "small") and (self.startPlayer):
            self.isTeam = True
        # Catch all player stats
        if (tag == "td") and (self.startPlayer):
            self.isStat = True

    def handle_data(self, data):
        # Store expert information and update date
        if (self.isExpert):
            self.expert.append(data)
        # Stores player data
        if (self.isName):
            self.name = data
        if (self.isTeam):
            self.team = data
        if (self.isStat):
            self.player.append(data)

    def handle_endtag(self, tag):
        if (tag == "table"):
            self.statsTable = False
            self.expertsTable = False
        if (tag == "a"):
            self.isName = False
        if (tag == "small"):
            self.isTeam = False
        if (tag == "td"):
            self.isStat = False
            self.isExpert = False
        if (tag == "tr") and (self.expertsTable):
            self.experts.append(self.expert)
            self.expert = []
        # Store each player into players table, and reset player
        if (tag == "tr") and (self.startPlayer):
            self.player.insert(0, self.team)
            self.player.insert(0, self.name)
            self.players.append(self.player)
            self.team = ''
            self.name = ''
            self.player = []
            self.startPlayer = False

class QS_HTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self)
        self.printDate   = False
        self.latest_date = False
        self.statsTable  = False
        self.isStat      = False
        self.isTeam      = False
        self.player      = []
        self.players     = []

    def handle_starttag(self, tag, attrs):
        # Catch player table
        if (tag == "tbody"):
            self.statsTable = True
        if (tag == "small") and (self.statsTable):
            self.isTeam = True
        if (tag == "td") and (self.statsTable):
            self.isStat = True

    def handle_data(self, data):
        if (self.isStat) and not (self.isTeam):
            self.player.append(data)

    def handle_endtag(self, tag):
        if (tag == "tbody") and (self.statsTable):
            self.statsTable = False
        if (tag == "small") and (self.isTeam):
            self.isTeam = False
        if (tag == "td") and (self.isStat):
            self.isStat = False
        # Store each player into players table, and reset player
        if (tag == "tr") and (self.statsTable):
            self.players.append(self.player)
            self.player = []

class Player:
    def __init__(self, name, team, pos, cat, fpts, cus_fpts, marg_val, auct_val, games,
                 qual_st, qs_per):
        self.name     = name
        self.team     = team
        self.pos      = pos
        self.cat      = cat
        self.fpts     = fpts
        self.cus_fpts = cus_fpts
        self.marg_val = marg_val
        self.auct_val = auct_val
        self.games    = games
        self.qual_st  = qual_st
        self.qs_per   = qs_per

    def __repr__(self):
        return repr((self.name, self.team, self.pos, self.cat, self.fpts, self.cus_fpts,
                     self.marg_val, self.auct_val, self.games, self.qual_st, self.qs_per))



# FUNCTIONS =================================================================================
# TODO comment

def parse_quality_starts( position ):
    if (VERBOSITY >= 2):
        print ("Parsing quality starts...")
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/players/quality-starts.php?position=" + position
    url = urllib.request.urlopen(addr)
    if (VERBOSITY >= 2):
        print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = QS_HTMLParser()
    if (VERBOSITY >= 2):
        print ("Parsing HTML...")
    parser.feed(source)

    qs_table = []
    for player in parser.players:
        name      = player[1]
        bad       = int(player[3])
        good      = int(player[5])
        great     = int(player[7])
        qual_per  = player[10]

        qs_table.append([name, (bad+good+great), (good*4 + great*6.25), qual_per])

    url.close()
    return qs_table

def parse_projections( position ):
    if (VERBOSITY >= 2):
        print ("Parsing projections...")
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/projections/" + position + ".php"
    url = urllib.request.urlopen(addr)
    if (VERBOSITY >= 2):
        print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = Projections_HTMLParser()
    if (VERBOSITY >= 2):
        print ("Parsing HTML...")
    parser.feed(source)

    # Print expert source information
    if (VERBOSITY >= 0):
        print ("Expert Source          Site           Published Date")
        for expert in parser.experts:
            if (expert):
                source = expert[0]
                site   = expert[1]
                date   = expert[2]
                print (source.ljust(20) + site.ljust(20) + date.ljust(20))

    url.close()
    return parser.players

def assign_quality_starts( name, qs_table ):
    qs_match  = False
    games     = 0
    qual_st   = 0
    qual_per  = ""

    for qs in qs_table:
        if (name in qs[0]):
            qs_match = True
            games    = qs[1]
            qual_st  = qs[2]
            qual_per = qs[3]
            break
    if not qs_match:
        if (VERBOSITY >= 2):
            print ("No quality starts name match for: " + name)

    return [games, qual_st, qual_per]

def assign_marginal_value( player_table, tier_val, total_marg_val ):
    for player in player_table:
        if (player.cus_fpts - tier_val[0]) >= 0:
            player.cat = "R" # Roster
            player.marg_val += float(player.cus_fpts - tier_val[0])
        if (player.cus_fpts - tier_val[1]) >= 0:
            player.cat = "TR" # Top Reserve
            player.marg_val += float(player.cus_fpts - tier_val[1])
        if (player.cus_fpts - tier_val[2]) >= 0:
            player.cat = "S" # Starter
            player.marg_val += float(player.cus_fpts - tier_val[2])
        if (player.cus_fpts - tier_val[3]) >= 0:
            player.cat = "ES" # Elite Starter
            player.marg_val += float(player.cus_fpts - tier_val[3])

        total_marg_val += player.marg_val

    return total_marg_val

def print_player_table( player_table ):
    i = 1
    for player in player_table:
        if (i == 1):
            print ('-' * 103)
            print ('  # | ' + "Player Name".center(30) + ' | ' + "Team " + ' | '
                    + "P." + ' | ' + "C." + ' | ' + "FPts." + ' | ' + "Cust. " +
                    ' | ' + "Marg. " + ' | ' + "Gms." + ' | ' + "Q.S. " + ' | ' +
                    "QS%" + ' | ')
            print ('-' * 103)
        print ("%3d" % i                 + ' | ' +
               player.name.ljust(30)     + ' | ' +
               player.team.ljust(5)      + ' | ' +
               player.pos                + ' | ' +
               player.cat.ljust(2)       + ' | ' +
               player.fpts.rjust(5)      + ' | ' +
               "%6.2f" % player.cus_fpts + ' | ' +
               "%6.2f" % player.marg_val + ' | ' +
               "%4d"   % player.games    + ' | ' +
               "%5.2f" % player.qual_st  + ' | ' +
               player.qs_per.rjust(3)    + ' | ' )

        i += 1

def player_tiers( position, player_table ):
    if ( position == "QB" ):
        r  = QB_ROSTER
        tr = QB_TOP_RESERVE
        s  = QB_STARTER
        es = QB_ELITE_STARTER
    elif (position == "RB" ):
        r  = RB_ROSTER
        tr = RB_TOP_RESERVE
        s  = RB_STARTER
        es = RB_ELITE_STARTER
    elif (position == "WR" ):
        r  = WR_ROSTER
        tr = WR_TOP_RESERVE
        s  = WR_STARTER
        es = WR_ELITE_STARTER
    elif (position == "TE" ):
        r  = TE_ROSTER
        tr = TE_TOP_RESERVE
        s  = TE_STARTER
        es = TE_ELITE_STARTER
    else:
        print (" *** ERROR: " + position + " not valid!")

    tier_val = [player_table[r].cus_fpts,
                player_table[tr].cus_fpts,
                player_table[s].cus_fpts,
                player_table[es].cus_fpts]

    if ( VERBOSITY >= 2 ):
        print (position + " Tier Cut-Offs:")
        print ("Elite Starter: " + player_table[es].name.ljust(30)
                        + "%.2f" % player_table[es].cus_fpts)
        print ("      Starter: " + player_table[s].name.ljust(30)
                        + "%.2f" % player_table[s].cus_fpts)
        print ("  Top Reserve: " + player_table[tr].name.ljust(30)
                        + "%.2f" % player_table[tr].cus_fpts)
        print ("       Roster: " + player_table[r].name.ljust(30)
                        + "%.2f" % player_table[r].cus_fpts)

    return tier_val

def main(argv):

    all_player_table = []
    tmp_table        = []
    total_marg_val   = 0.0

    try:
        opts, args = getopt.getopt(argv,"hv:o:")
    except getopt.GetoptError:
        print (HELP_MSG)
        sys.exit(2)
    for opt, arg in opts:
        if (opt == '-h'):
            print (HELP_MSG)
            sys.exit()
        elif (opt == '-v'):
            global VERBOSITY
            VERBOSITY = int(arg)
        elif (opt == '-o'):
            global OUT_FILE
            OUT_FILE = arg

    if not OUT_FILE:
        print ("No output file selected, skipping file write")
    else:
        if (VERBOSITY >= 2):
            print ("Output file is", OUT_FILE)

    # FILE OVERWRITE ========================================================================
    # Check if file exists. If yes, asks for confirmation to overwrite or exits. If
    # no, the file is automatically created
    if OUT_FILE:
        if (os.path.exists(OUT_FILE)):
            ret = input("File " + OUT_FILE + " exists. Would you like to overwrite? [Y/n]: ")
            if (ret == "Y"):
                print ("Overwriting", OUT_FILE)
                f = open(OUT_FILE, "w")
            else:
                print ("Exiting without overwriting", OUT_FILE)
                sys.exit()
        else:
            if (VERBOSITY >= 2):
                print ("No file named", OUT_FILE, "detected in directory, creating new file.")

            f = open(OUT_FILE, "w")


    # QBs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== QBs ==========')

    qs_table = parse_quality_starts("QB")

    player_table = parse_projections("qb")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building QB position table...")
    for player in player_table:
        name      = player[0].replace("\\","")
        team      = player[1]
        pass_att  = player[2].replace(',','')
        pass_cmp  = player[3].replace(',','')
        pass_yds  = player[4].replace(',','')
        pass_tds  = player[5].replace(',','')
        pass_ints = player[6].replace(',','')
        rush_att  = player[7].replace(',','')
        rush_yds  = player[8].replace(',','')
        rush_tds  = player[9].replace(',','')
        fmbls     = player[10].replace(',','')
        fpts      = player[11].replace(',','')
        cus_fpts  = ((PASS_CMP_PTS * float(pass_cmp )) +
                     (PASS_YRD_PTS * float(pass_yds )) +
                     (PASS_TD_PTS  * float(pass_tds )) +
                     (INT_PTS      * float(pass_ints)) +
                     (RUSH_ATT_PTS * float(rush_att )) +
                     (RUSH_YRD_PTS * float(rush_yds )) +
                     (RUSH_TD_PTS  * float(rush_tds )) +
                     (FUMB_PTS     * float(fmbls    )))

        # Apply quality starts information
        [games, qual_st, qual_per] = assign_quality_starts(name, qs_table)

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "QB", "", fpts, cus_fpts, 0.0, 0.0, games, qual_st, qual_per))

    # Apply position table as temporary table sorted on custom fantasy points
    if (VERBOSITY >= 2):
        print ("Sorting table by custom fantasy points...")
    qb_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    if (VERBOSITY >= 2):
        print ("Creating player tiers...")
    qb_tier_val = player_tiers ("QB", qb_table)

    # Apply marginal value calculation
    if (VERBOSITY >= 2):
        print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (qb_table, qb_tier_val, total_marg_val)

    if (VERBOSITY >= 1):
        print ("Printing player table...")
        print_player_table (qb_table)

    # Clear temporary table, add position to all-players list
    tmp_table = []
    all_player_table.extend(qb_table)

    # RBs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== RBs ==========')

    qs_table = parse_quality_starts("RB")

    player_table = parse_projections("rb")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building RB position table...")
    for player in player_table:
        name     = player[0].replace("\\","")
        team     = player[1]
        rush_att = player[2].replace(',','')
        rush_yds = player[3].replace(',','')
        rush_tds = player[4].replace(',','')
        rec_rec  = player[5].replace(',','')
        rec_yds  = player[6].replace(',','')
        rec_tds  = player[7].replace(',','')
        fmbls    = player[8].replace(',','')
        fpts     = player[9].replace(',','')
        cus_fpts = ((RUSH_ATT_PTS * float(rush_att)) +
                    (RUSH_YRD_PTS * float(rush_yds)) +
                    (RUSH_TD_PTS  * float(rush_tds)) +
                    (RECEP_PTS    * float(rec_rec )) +
                    (REC_YRD_PTS  * float(rec_yds )) +
                    (REC_TD_PTS   * float(rec_tds )) +
                    (FUMB_PTS     * float(fmbls   )))

        # Apply quality starts information
        [games, qual_st, qual_per] = assign_quality_starts(name, qs_table)

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "RB", "", fpts, cus_fpts, 0.0, 0.0, games, qual_st, qual_per))

    # Apply position table as temporary table sorted on custom fantasy points
    if (VERBOSITY >= 2):
        print ("Sorting table by custom fantasy points...")
    rb_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    if (VERBOSITY >= 2):
        print ("Creating player tiers...")
    rb_tier_val = player_tiers ("RB", rb_table)

    # Apply marginal value calculation
    if (VERBOSITY >= 2):
        print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (rb_table, rb_tier_val, total_marg_val)

    if (VERBOSITY >= 1):
        print ("Printing player table...")
        print_player_table (rb_table)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(rb_table)

    # WRs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== WRs ==========')

    qs_table = parse_quality_starts("WR")

    player_table = parse_projections("wr")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building WR position table...")
    for player in player_table:
        name     = player[0].replace("\\","")
        team     = player[1]
        rush_att = player[2].replace(',','')
        rush_yds = player[3].replace(',','')
        rush_tds = player[4].replace(',','')
        rec_rec  = player[5].replace(',','')
        rec_yds  = player[6].replace(',','')
        rec_tds  = player[7].replace(',','')
        fmbls    = player[8].replace(',','')
        fpts     = player[9].replace(',','')
        cus_fpts = ((RUSH_ATT_PTS * float(rush_att)) +
                    (RUSH_YRD_PTS * float(rush_yds)) +
                    (RUSH_TD_PTS  * float(rush_tds)) +
                    (RECEP_PTS    * float(rec_rec )) +
                    (REC_YRD_PTS  * float(rec_yds )) +
                    (REC_TD_PTS   * float(rec_tds )) +
                    (FUMB_PTS     * float(fmbls   )))

        # Apply quality starts information
        [games, qual_st, qual_per] = assign_quality_starts(name, qs_table)

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "WR", "", fpts, cus_fpts, 0.0, 0.0, games, qual_st, qual_per))

    # Apply position table as temporary table sorted on custom fantasy points
    if (VERBOSITY >= 2):
        print ("Sorting table...")
    wr_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    if (VERBOSITY >= 2):
        print ("Creating player tiers...")
    wr_tier_val = player_tiers ("WR", wr_table)

    # Apply marginal value calculation
    if (VERBOSITY >= 2):
        print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (wr_table, wr_tier_val, total_marg_val)

    if (VERBOSITY >= 1):
        print ("Printing player table...")
        print_player_table (wr_table)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(wr_table)

    # TEs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== TEs ==========')

    qs_table = parse_quality_starts("TE")

    player_table = parse_projections("te")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building TE position table...")
    for player in player_table:
        name     = player[0].replace("\\","")
        team     = player[1]
        rec_rec  = player[2].replace(',','')
        rec_yds  = player[3].replace(',','')
        rec_tds  = player[4].replace(',','')
        fmbls    = player[5].replace(',','')
        fpts     = player[6].replace(',','')
        cus_fpts = ((RECEP_PTS    * float(rec_rec)) +
                    (REC_YRD_PTS  * float(rec_yds)) +
                    (REC_TD_PTS   * float(rec_tds)) +
                    (FUMB_PTS     * float(fmbls  )))

        # Apply quality starts information
        [games, qual_st, qual_per] = assign_quality_starts(name, qs_table)

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "TE", "", fpts, cus_fpts, 0.0, 0.0, games, qual_st, qual_per))

    # Apply position table as temporary table sorted on custom fantasy points
    if (VERBOSITY >= 2):
        print ("Sorting table...")
    te_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    if (VERBOSITY >= 2):
        print ("Creating player tiers...")
    te_tier_val = player_tiers ("TE", te_table)

    # Apply marginal value calculation
    if (VERBOSITY >= 2):
        print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (te_table, te_tier_val, total_marg_val)

    if (VERBOSITY >= 1):
        print ("Printing player table...")
        print_player_table (te_table)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(te_table)

    # AUCTION VALUES ========================================================================
    marg_pts_per_dollar = total_marg_val / DISCR_MONEY
    if (VERBOSITY >= 1):
        print ('\n===== CALCULATIONS ======')
        print ("Total Marginal Value   : " + "%.3f" % total_marg_val)
        print ("Marg. Points Per Dollar: " + "%.3f" % marg_pts_per_dollar)
        print ("Keeper Value Inflation:  " + "%.3f" % KEEPER_INFLATION)

    # Sort all players by marginal value to get value rankings
    if (VERBOSITY >= 2):
        print ("Sorting all players by marginal value...")
    tmp_table = all_player_table
    all_player_table = sorted(tmp_table, key=lambda player: player.marg_val, reverse=True)

    # Write column categories to file
    if OUT_FILE:
        f.write("Player Name"              + '\t' +
                "Team"                     + '\t' +
                "Position"                 + '\t' +
                "Category"                 + '\t' +
                "Projected Fantasy Points" + '\t' +
                "Custom Fantasy Points"    + '\t' +
                "Marginal Value"           + '\t' +
                "Auction Value"            + '\t' +
                "Budget Percentage"        + '\t' +
                "Static Inflation"         + '\t' +
                "Dynamic Inflation"        + '\t' +
                "Depth Chart"              + '\t' +
                "Injury"                   + '\t' +
                "Status"                   + '\t' +
                "Notes"                    + '\t' +
                "Purchase Price"           + '\t' +
                "Realized Value"           + '\t' +
                "Owner"                    + '\n')

    budget_per = 0.0
    inflation  = 0.0
    i = 1
    # Write player table and apply auction value, budget percentage, and static inflation
    if (VERBOSITY >= 2):
        print ("Applying auction value, budget percentage, and static inflation...")
    for player in all_player_table:
        # Calculate remaining values
        player.auct_val = math.ceil((player.marg_val / marg_pts_per_dollar) + 1)
        budget_per      = ( player.auct_val / AUCTION_MONEY ) * 100
        inflation       = player.auct_val * KEEPER_INFLATION

        # Write player data to file
        if OUT_FILE:
            f.write(player.name                  + '\t' +
                    player.team                  + '\t' +
                    player.pos                   + '\t' +
                    player.cat                   + '\t' +
                    player.fpts                  + '\t' +
                    "%.2f" % player.cus_fpts     + '\t' +
                    "%.2f" % player.marg_val     + '\t' +
                    "$%d" % int(player.auct_val) + '\t' +
                    "%.1f%%" % budget_per        + '\t' +
                    "$%d" % int(inflation)       + '\n' )

        if (VERBOSITY >= 1):
            if (i == 1):
                print ('-' * 102)
                print ('  # | ' + "Player Name".center(30) + ' | ' + "Team " + ' | '
                      + "P." + ' | ' + "C." + ' | ' + "FPts." + ' | ' + "Cust. "
                      + ' | ' + "Marg. " + ' | ' + "A.V." + ' | ' + "B.%" + ' | '
                      + "Inf." + ' | ')
                print ('-' * 102)
            print ("%3d" % i                      + ' | ' +
                   player.name.ljust(30)          + ' | ' +
                   player.team.ljust(5)           + ' | ' +
                   player.pos                     + ' | ' +
                   player.cat.ljust(2)            + ' | ' +
                   player.fpts.rjust(5)           + ' | ' +
                   "%6.2f" % player.cus_fpts      + ' | ' +
                   "%6.2f" % player.marg_val      + ' | ' +
                   "$%3d"  % int(player.auct_val) + ' | ' +
                   "%2d%%" % int(budget_per)      + ' | ' +
                   "$%3d"  % int(inflation)       + ' | ' )

        i += 1
    # END ===================================================================================
    if (VERBOSITY >= 2):
        print ('\n========== END ==========')

    # Indicate success
    if OUT_FILE:
        # Close the file
        f.close()

        print ("File created: " + OUT_FILE)
        print ("Import into Excel using tab delimiters")

# MAIN ======================================================================================
if __name__ == "__main__":
   main(sys.argv[1:])

