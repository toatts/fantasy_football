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
# 0 = minimal, 1 = chart display, 2 = all (debug messaging)
VERBOSITY        = 1
OUT_FILE         = ''
DRAFT_TYPE       = "auction"
HELP_MSG  = (
"Usage: python ff_draft_organizer.py <-opt setting>\n"
"-option      [description]\n"
"-h           [help file, prints out this message]\n"
"-v <0-2>     [verbosity, 0 = minimal, 1 = chart display (default), 2 = debug]\n"
"-o <file>    [output file, tab separated value type, if not specified then none created]\n"
"-t <type>    [draft type, use snake or auction (default)]\n"
)


# CLASSES ===================================================================================
# Consensus Projections HMTL Parsing
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

# Quality Starts HTML Parsing
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

# Depth Charts HTML Parsing
class DC_HTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self)
        self.teamTable  = False
        self.header     = False
        self.isData     = False
        self.isPlayer   = False
        self.player     = []
        self.players    = []

    def handle_starttag(self, tag, attrs):
        if (tag == "table"):
            self.teamTable = True
        if (tag == "tr"):
            for (attr, data) in attrs:
                if (attr == "style"):
                    self.header = True
        if (tag == "td") and (self.teamTable) and not (self.header):
            self.isData = True
        if (tag == "br") and (self.teamTable):
            if (self.isPlayer):
                self.isPlayer = False
                self.players.append(self.player)
            self.player = []
        if (tag == "a") and (self.teamTable) and not (self.header):
            self.isPlayer = True

    def handle_data(self, data):
        if (self.isData):
            self.player.append(data)

    def handle_endtag(self, tag):
        if (tag == "table") and (self.teamTable):
            self.teamTable = False
        if (tag == "td") and (self.isData):
            self.isData = False
        if (tag == "tr") and (self.teamTable):
            self.header = False

# Injury Lists HTML Parsing
class Injury_HTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self)
        self.teamTable  = False
        self.isData     = False
        self.isPlayer   = False
        self.player     = []
        self.players    = []

    def handle_starttag(self, tag, attrs):
        # Catch player table
        if (tag == "table"):
            for (attr, data) in attrs:
                if ((attr == "class") and (data == "data")):
                    self.teamTable = True
        if (tag == "tr"):
            for (attr, data) in attrs:
                if ((attr == "class") and ((data == "row1") or (data == "row2"))):
                    self.isPlayer = True
        if (tag == "td") and (self.teamTable) and (self.isPlayer):
            self.isData = True

    def handle_data(self, data):
        if (self.isData):
            if (data != "No Injuries Reported"):
                self.player.append(data)

    def handle_endtag(self, tag):
        if (tag == "table") and (self.teamTable):
            self.teamTable = False
        if (tag == "td") and (self.isData):
            self.isData = False
        if (tag == "tr") and (self.isPlayer):
            self.isPlayer = False
            if (self.player):
                self.players.append(self.player)
                self.player = []

# Fantasy Football Player Class
class Player:
    def __init__(self, name, team, pos, cat, fpts, cus_fpts, marg_val, auct_val,
                 budget, s_infl, d_infl, depth, games, qual_st, qs_per, injury,
                 status, notes, price, real_val, owner):
        self.name     = name
        self.team     = team
        self.pos      = pos
        self.cat      = cat
        self.fpts     = fpts
        self.cus_fpts = cus_fpts
        self.marg_val = marg_val
        self.auct_val = auct_val
        self.budget   = budget
        self.s_infl   = s_infl
        self.d_infl   = d_infl
        self.depth    = depth
        self.games    = games
        self.qual_st  = qual_st
        self.qs_per   = qs_per
        self.injury   = injury
        self.status   = status
        self.notes    = notes
        self.price    = price
        self.real_val = real_val
        self.owner    = owner

    def __repr__(self):
        return repr((self.name, self.team, self.pos, self.cat, self.fpts, self.cus_fpts,
                     self.marg_val, self.auct_val, self.budget, self.s_infl, self.d_infl,
                     self.depth, self.games, self.qual_st, self.qs_per, self.injury,
                     self.status, self.notes, self.price, self.real_val, self.owner))


# FUNCTIONS =================================================================================
def parse_depth_charts():
    if (VERBOSITY >= 2):
        print ("Parsing depth charts...")
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/depth-charts.php"
    url = urllib.request.urlopen(addr)
    if (VERBOSITY >= 2):
        print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = DC_HTMLParser()
    if (VERBOSITY >= 2):
        print ("Parsing HTML...")
    parser.feed(source)

    dc_table = []
    for player in parser.players:
        depth = player[0].replace(" ", "")
        name  = player[1].replace("\\'", "")

        dc_table.append([name, depth])

    url.close()
    return dc_table

def parse_injuries():
    if (VERBOSITY >= 2):
        print ("Parsing injuries...")
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.cbssports.com/nfl/injuries"
    url = urllib.request.urlopen(addr)
    if (VERBOSITY >= 2):
        print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = Injury_HTMLParser()
    if (VERBOSITY >= 2):
        print ("Parsing HTML...")
    parser.feed(source)

    inj_table = []
    for player in parser.players:
        inj_date = player[0]
        pos      = player[1]
        name     = player[2].replace("\\'", "")
        injury   = player[3]
        status   = player[4]
        detail   = player[5]
        merge    = inj_date + ", " + injury + ", " + detail

        if ((pos == "RB") or (pos == "QB") or (pos == "WR") or (pos == "TE")):
            inj_table.append([name, merge, status])

    url.close()
    return inj_table

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
        name      = player[1].replace("\\'", "")
        bad       = int(player[3])
        good      = int(player[5])
        great     = int(player[7])
        qual_per  = player[10]
                               # games           quality start stat     % games quality
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

def assign_quality_starts( player_table ):
    qs_table   = []
    tmp_table  = parse_quality_starts("QB")
    qs_table.extend(tmp_table)
    tmp_table  = parse_quality_starts("RB")
    qs_table.extend(tmp_table)
    tmp_table  = parse_quality_starts("WR")
    qs_table.extend(tmp_table)
    tmp_table  = parse_quality_starts("TE")
    qs_table.extend(tmp_table)

    name_match = False

    for qs_player in qs_table:
        name = qs_player[0].replace("'", "")
        for player in player_table:
            if (name in player.name):
                name_match     = True
                player.games   = qs_player[1]
                player.qual_st = qs_player[2]
                player.qs_per  = qs_player[3]
                break
        if not name_match:
            if (VERBOSITY >= 2):
                print ("WARNING: " + name + " from quality starts table \
                        not found in player table!")

def assign_depth_charts( player_table ):
    dc_table   = parse_depth_charts()

    name_match = False

    for dc_player in dc_table:
        name = dc_player[0].replace("'", "")
        for player in player_table:
            if (name in player.name):
                name_match     = True
                player.depth   = dc_player[1]
                break
        if not name_match:
            if (VERBOSITY >= 2):
                print ("WARNING: " + name + " from depth chart table \
                        not found in player table!")

def assign_injuries( player_table ):
    inj_table  = parse_injuries()

    name_match = False

    for inj_player in inj_table:
        name = inj_player[0].replace("'", "")
        for player in player_table:
            if (name in player.name):
                name_match     = True
                player.injury  = inj_player[1]
                player.status  = inj_player[2]
                break
        if not name_match:
            if (VERBOSITY >= 2):
                print ("WARNING: " + name + " from injury chart table \
                        not found in player table!")

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

def print_player_table( player_table, out_file = False ):
    i = 1
    for player in player_table:
        if (out_file):
            if (DRAFT_TYPE == "auction"):
                if (i == 1):
                    out_file.write("Player Name"              + '\t' +
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
                                   "Games Played Last Season" + '\t' +
                                   "Quality Start (Max:100)"  + '\t' +
                                   "Quality Start Percentage" + '\t' +
                                   "Injury"                   + '\t' +
                                   "Status"                   + '\t' +
                                   "Notes"                    + '\t' +
                                   "Purchase Price"           + '\t' +
                                   "Realized Value"           + '\t' +
                                   "Owner"                    + '\n')

                out_file.write(player.name                  + '\t' +
                               player.team                  + '\t' +
                               player.pos                   + '\t' +
                               player.cat                   + '\t' +
                               player.fpts                  + '\t' +
                               "%.2f" % player.cus_fpts     + '\t' +
                               "%.2f" % player.marg_val     + '\t' +
                               "$%d" % int(player.auct_val) + '\t' +
                               "%.1f%%" % player.budget     + '\t' +
                               "$%d" % int(player.s_infl)   + '\t' +
                               player.d_infl                + '\t' +
                               player.depth                 + '\t' +
                               "%d" % player.games          + '\t' +
                               "%.2f" % player.qual_st      + '\t' +
                               player.qs_per                + '\t' +
                               player.injury                + '\t' +
                               player.status                + '\t' +
                               player.notes                 + '\t' +
                               player.price                 + '\t' +
                               player.real_val              + '\t' +
                               player.owner                 + '\n' )
            else: # Snake draft
                if (i == 1):
                    out_file.write("Player Name"              + '\t' +
                                   "Team"                     + '\t' +
                                   "Position"                 + '\t' +
                                   "Category"                 + '\t' +
                                   "Projected Fantasy Points" + '\t' +
                                   "Custom Fantasy Points"    + '\t' +
                                   "Marginal Value"           + '\t' +
                                   "Depth Chart"              + '\t' +
                                   "Games Played Last Season" + '\t' +
                                   "Quality Start (Max:100)"  + '\t' +
                                   "Quality Start Percentage" + '\t' +
                                   "Injury"                   + '\t' +
                                   "Status"                   + '\t' +
                                   "Notes"                    + '\t' +
                                   "Owner"                    + '\n')

                out_file.write(player.name                  + '\t' +
                               player.team                  + '\t' +
                               player.pos                   + '\t' +
                               player.cat                   + '\t' +
                               player.fpts                  + '\t' +
                               "%.2f" % player.cus_fpts     + '\t' +
                               "%.2f" % player.marg_val     + '\t' +
                               player.depth                 + '\t' +
                               "%d" % player.games          + '\t' +
                               "%.2f" % player.qual_st      + '\t' +
                               player.qs_per                + '\t' +
                               player.injury                + '\t' +
                               player.status                + '\t' +
                               player.notes                 + '\t' +
                               player.owner                 + '\n' )


        if (VERBOSITY >= 1):
            if (DRAFT_TYPE == "auction"):
                if (i == 1):
                    print ('-' * 130)
                    print ('  # | ' + "Player Name".center(30) + ' | ' + "Team " + ' | '
                            + "P." + ' | ' + "C." + ' | ' + "FPts." + ' | ' + "Cust. " +
                            ' | ' + "Marg. " + ' | ' + "A.V." + ' | ' + "B.%" + ' | ' +
                            "Inf." + ' | ' + "DC " + ' | ' + "Gms." + ' | ' + " Q.S." +
                            ' | ' + " QS%" + ' | ')
                    print ('-' * 130)

                print ("%3d" % i                      + ' | ' +
                       player.name.ljust(30)          + ' | ' +
                       player.team.ljust(5)           + ' | ' +
                       player.pos                     + ' | ' +
                       player.cat.ljust(2)            + ' | ' +
                       player.fpts.rjust(5)           + ' | ' +
                       "%6.2f" % player.cus_fpts      + ' | ' +
                       "%6.2f" % player.marg_val      + ' | ' +
                       "$%d"   % int(player.auct_val) + ' | ' +
                       "%.1f%%" % player.budget       + ' | ' +
                       "$%d"   % int(player.s_infl)   + ' | ' +
                       player.depth.rjust(3)          + ' | ' +
                       "%4d"   % player.games         + ' | ' +
                       "%5.2f" % player.qual_st       + ' | ' +
                       player.qs_per.rjust(4)         + ' | ' )

            else: # Snake draft
                if (i == 1):
                    print ('-' * 110)
                    print ('  # | ' + "Player Name".center(30) + ' | ' + "Team " + ' | '
                            + "P." + ' | ' + "C." + ' | ' + "FPts." + ' | ' + "Cust. " +
                            ' | ' + "Marg. " + ' | ' + "DC " + ' | ' + "Gms." + ' | ' +
                            " Q.S." + ' | ' + " QS%" + ' | ')
                    print ('-' * 110)

                print ("%3d" % i                      + ' | ' +
                       player.name.ljust(30)          + ' | ' +
                       player.team.ljust(5)           + ' | ' +
                       player.pos                     + ' | ' +
                       player.cat.ljust(2)            + ' | ' +
                       player.fpts.rjust(5)           + ' | ' +
                       "%6.2f" % player.cus_fpts      + ' | ' +
                       "%6.2f" % player.marg_val      + ' | ' +
                       player.depth.rjust(3)          + ' | ' +
                       "%4d"   % player.games         + ' | ' +
                       "%5.2f" % player.qual_st       + ' | ' +
                       player.qs_per.rjust(4)         + ' | ' )

        i += 1


# MAIN ======================================================================================
def main(argv):

    all_player_table = []
    tmp_table        = []
    total_marg_val   = 0.0

    try:
        opts, args = getopt.getopt(argv,"hv:o:t:")
    except getopt.GetoptError:
        print (HELP_MSG)
        sys.exit(2)
    for opt, arg in opts:
        if (opt == '-h'):
            print (HELP_MSG)
            sys.exit()
        elif (opt == '-v'):
            global VERBOSITY
            if ((arg == '0') or (arg == '1') or (arg == '2')):
                VERBOSITY = int(arg)
            else:
                print (HELP_MSG)
                sys.exit(2)
        elif (opt == '-o'):
            global OUT_FILE
            OUT_FILE = arg
        elif (opt == '-t'):
            global DRAFT_TYPE
            if (arg == 'snake'):
                DRAFT_TYPE = arg
            else:
                print (HELP_MSG)
                sys.exit(2)

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

    player_table = parse_projections("qb")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building QB position table...")
    for player in player_table:
        name      = player[0].replace("\\'","")
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

        tmp_table.append(Player(name, team, "QB", "", fpts, cus_fpts, 0.0, 0.0,
                                0.0, 0.0, "", "", 0, 0.0, "", "", "", "", "", "", ""))

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

    if (VERBOSITY >= 2):
        print ("Printing player table...")
        print_player_table (qb_table)

    # Clear temporary table, add position to all-players list
    tmp_table = []
    all_player_table.extend(qb_table)

    # RBs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== RBs ==========')

    player_table = parse_projections("rb")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building RB position table...")
    for player in player_table:
        name     = player[0].replace("\\'","")
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

        tmp_table.append(Player(name, team, "RB", "", fpts, cus_fpts, 0.0, 0.0,
                                0.0, 0.0, "", "", 0, 0.0, "", "", "", "", "", "", ""))

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

    if (VERBOSITY >= 2):
        print ("Printing player table...")
        print_player_table (rb_table)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(rb_table)

    # WRs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== WRs ==========')

    player_table = parse_projections("wr")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building WR position table...")
    for player in player_table:
        name     = player[0].replace("\\'","")
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

        tmp_table.append(Player(name, team, "WR", "", fpts, cus_fpts, 0.0, 0.0,
                                0.0, 0.0, "", "", 0, 0.0, "", "", "", "", "", "", ""))

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

    if (VERBOSITY >= 2):
        print ("Printing player table...")
        print_player_table (wr_table)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(wr_table)

    # TEs ===================================================================================
    if (VERBOSITY >= 0):
        print ('\n========== TEs ==========')

    player_table = parse_projections("te")

    # Apply stats for each player
    if (VERBOSITY >= 2):
        print ("Building TE position table...")
    for player in player_table:
        name     = player[0].replace("\\'","")
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

        tmp_table.append(Player(name, team, "TE", "", fpts, cus_fpts, 0.0, 0.0,
                                0.0, 0.0, "", "", 0, 0.0, "", "", "", "", "", "", ""))

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

    if (VERBOSITY >= 2):
        print ("Printing player table...")
        print_player_table (te_table)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(te_table)

    # AUCTION VALUES ========================================================================
    # Apply quality starts information
    assign_quality_starts( all_player_table )

    # Apply depth chart information
    assign_depth_charts( all_player_table )

    # Apply injury information
    assign_injuries( all_player_table )

    if (DRAFT_TYPE == "auction"):
        marg_pts_per_dollar = total_marg_val / DISCR_MONEY
        if (VERBOSITY >= 1):
            print ('\n===== CALCULATIONS ======')
            print ("Total Marginal Value   : " + "%.3f" % total_marg_val)
            print ("Marg. Points Per Dollar: " + "%.3f" % marg_pts_per_dollar)
            print ("Keeper Value Inflation : " + "%.3f" % KEEPER_INFLATION)

        if (VERBOSITY >= 2):
            print ("Applying auction value, budget percentage, and static inflation...")
        for player in all_player_table:
            # Calculate remaining values
            player.auct_val = math.ceil((player.marg_val / marg_pts_per_dollar) + 1)
            player.budget   = ( player.auct_val / AUCTION_MONEY ) * 100
            player.s_infl   = player.auct_val * KEEPER_INFLATION

    if (VERBOSITY >= 2):
        print ("Sorting all players by marginal value, then custom fantasy points...")
    tmp_table = all_player_table
    all_player_table = sorted(tmp_table, key=lambda player : (player.marg_val,
                              player.cus_fpts), reverse=True)

    # Print all player table
    if OUT_FILE:
        print ("Printing sorted list to file, " + OUT_FILE + "...")
        print_player_table (all_player_table, f)

    else:
        print ("Printing sorted list...")
        print_player_table (all_player_table)

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

