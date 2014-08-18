# HEADER ====================================================================================
# File   : ff_draft_organizer.py
# Author : Jay Oatts
# Email  : jay.oatts@gmail.com
# Date   : 8/18/2014
# Version: 0.3
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

# TODO:
# 1. Add command line options (or asks if not input) (verbosity setting first, create CSV y/n, output file)
# 2. Change league scoring rules to an importable configuration file
# 2. Add quality starts to list (http://www.fantasypros.com/nfl/players/quality-starts.php?position=QB)
# 3. Use http://www.fantasypros.com/nfl/depth-charts.php for depth chart additions
# 4. Modify for snake draft
# 5. Run everything under main()

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


# TODO: moving to ff_draft_info.yaml
# USER DEFINES ==============================================================================
# League Scoring Rules
PASS_CMP_PTS = config.pass_completion # 0.05
PASS_YRD_PTS = config.passing_yard # 0.04
PASS_TD_PTS  = config.passing_touchdown # 4.0
INT_PTS      = config.interception # -3.0
RUSH_ATT_PTS = config.rushing_attempt # 0.1
RUSH_YRD_PTS = config.rushing_yard # 0.1
RUSH_TD_PTS  = config.rushing_touchdown # 6.0
FUMB_PTS     = config.fumble # -2.0
RECEP_PTS    = config.reception # 1.0
REC_YRD_PTS  = config.receiving_yard # 0.1
REC_TD_PTS   = config.receiving_touchdown # 6.0

# Auction Money
TOTAL_TEAMS   =  config.teams # 12
AUCTION_MONEY = config.auction_money # 220
ROSTER_SLOTS  = config.roster_slots # 17
TOTAL_MONEY   = AUCTION_MONEY * TOTAL_TEAMS
DISCR_MONEY   = TOTAL_MONEY - (ROSTER_SLOTS * TOTAL_TEAMS)
# Sum of teams keeper spending price
KEEPER_MONEY_SPENT = config.keeper_money_used # (18+82+73+46+37+13+16+25+58+36+19+112)
# Sum of the projected value of players that teams are keeping
KEEPER_VALUE = config.keeper_value # 1090
# Inflation multiplier, impacting remaining players in draft
KEEPER_INFLATION = (TOTAL_MONEY - KEEPER_MONEY_SPENT) / (TOTAL_MONEY - KEEPER_VALUE)

# Marginal Scoring
# ROSTER        = number of expected players drafted at that position (approximation)
# TOP_RESERVE   = number of starters at position * 1.5
# STARTER       = number of starters at position
# ELITE_STARTER = number of starters at position * 0.5
# NOTE: subtracted 1 for indexing purposes
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


# CLASSES ===================================================================================
class MyHTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self)
        self.printDate = False
        self.latest_date = False
        self.statsTable = False
        self.startPlayer = False
        self.isName = False
        self.isTeam = False
        self.isStat = False
        self.player = []
        self.players = []
        self.name = ''
        self.team = ''
        self.updateDate = ''

    def handle_starttag(self, tag, attrs):
        # Catch table update date
        if (tag == "div"):
            for (attr, data) in attrs:
                if ((attr == "class") and (data == "latest-update")):
                    self.latest_date = True
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
        # Prints the date each table was updated
        if (self.printDate):
            self.updateDate = data.replace(r'\t', '')
            print ("********************************")
            print ("* Table updated" + self.updateDate)
            print ("********************************")
        # Stores player data
        if (self.isName):
            self.name = data
        if (self.isTeam):
            self.team = data
        if (self.isStat):
            self.player.append(data)

    def handle_endtag(self, tag):
        if (tag == "a") and (self.latest_date == True):
            self.printDate = True
        if (tag == "div") and (self.printDate):
            self.printDate = False
            self.latest_date = False
        if (tag == "table") and (self.statsTable):
            self.statsTable = False
        if (tag == "a") and (self.isName):
            self.isName = False
        if (tag == "small") and (self.isTeam):
            self.isTeam = False
        if (tag == "td") and (self.isStat):
            self.isStat = False
        # Store each player into players table, and reset player
        if (tag == "tr") and (self.startPlayer):
            self.player.insert(0, self.team)
            self.player.insert(0, self.name)
            self.players.append(self.player)
            self.player = []
            self.team = ''
            self.name = ''
            self.startPlayer = False

class Player:
    def __init__(self, name, team, pos, cat, fpts, cus_fpts, marg_val, auct_val):
        self.name = name
        self.team = team
        self.pos = pos
        self.cat = cat
        self.fpts = fpts
        self.cus_fpts = cus_fpts
        self.marg_val = marg_val
        self.auct_val = auct_val

    def __repr__(self):
        return repr((self.name, self.team, self.pos, self.cat, self.fpts, self.cus_fpts, self.marg_val, self.auct_val))



# FUNCTIONS =================================================================================
# TODO comment
def assign_marginal_value( player_table, tier_val, total_marg_val ):
    i = 1
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

        if (VERBOSITY > 1):
            if (i == 1):
                print ('-' * 82)
                print ('  # | ' + "Player Name".center(30) + ' | ' + "Team " + ' | '
                        + "P." + ' | ' + "C." + ' | ' + "FPts." + ' | ' + "Cust. " +
                        ' | ' + "Marg. " + ' | ')
                print ('-' * 82)
            print ("%3d" % i                 + ' | ' +
                   player.name.ljust(30)     + ' | ' +
                   player.team.ljust(5)      + ' | ' +
                   player.pos                + ' | ' +
                   player.cat.ljust(2)       + ' | ' +
                   player.fpts.rjust(5)      + ' | ' +
                   "%6.2f" % player.cus_fpts + ' | ' +
                   "%6.2f" % player.marg_val + ' | ')

        i += 1

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

    if ( VERBOSITY > 1 ):
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

    # GLOBALS ===============================================================================
    all_player_table = []
    tmp_table = []
    total_marg_val = 0.0
# TODO: use enum for verbosity?
    global VERBOSITY
    # 0 = none/little, 1 = chart displays, 2 = all (debug messaging)
    OUT_FILE  = ''
    HELP_MSG  = "python ff_draft_organizer.py -v <verbosity (0-2)> -o <output file>"
# TODO: if out file defined, create csv, otherwise just use standard output (level 1 verbosity)

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
            VERBOSITY = int(arg)
        elif (opt == '-o'):
            OUT_FILE = arg
        else:
            print ("Unrecognized command line option [", opt, "] with argument [", arg, "]")
            sys.exit(2)

    print ("Output file is", OUT_FILE)

    # FILE OVERWRITE ========================================================================
    # Check if file exists. If yes, asks for confirmation to overwrite or exits. If
    # no, the file is automatically created
    if (os.path.exists(OUT_FILE)):
        ret = input("File " + OUT_FILE + " exists. Would you like to overwrite? [Y/n]: ")
        if (ret == "Y"):
            print ("Overwriting", OUT_FILE)
            f = open(OUT_FILE, "w")
        else:
            print ("Exiting without overwriting", OUT_FILE)
            sys.exit()
    else:
        print ("No file named", OUT_FILE, "detected in directory, creating new file.")
        f = open(OUT_FILE, "w")


    # QBs ===================================================================================
    print ('\n========== QBs ==========')
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/projections/qb.php"
    url = urllib.request.urlopen(addr)
    print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = MyHTMLParser()
    print ("Parsing HTML...")
    parser.feed(source)

    # Apply stats for each player
    print ("Building QB position table...")
    for player in parser.players:
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

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "QB", "", fpts, cus_fpts, 0.0, 0.0))

    # Apply position table as temporary table sorted on custom fantasy points
    print ("Sorting table...")
    qb_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    print ("Creating player tiers...")
    qb_tier_val = player_tiers ("QB", qb_table)

    # Apply marginal value calculation
    print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (qb_table, qb_tier_val, total_marg_val)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(qb_table)
    url.close()

    # RBs ===================================================================================
    print ('\n========== RBs ==========')
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/projections/rb.php"
    url = urllib.request.urlopen(addr)
    print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = MyHTMLParser()
    print ("Parsing HTML...")
    parser.feed(source)

    # Apply stats for each player
    print ("Building RB position table...")
    for player in parser.players:
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

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "RB", "", fpts, cus_fpts, 0.0, 0.0))

    # Apply position table as temporary table sorted on custom fantasy points
    print ("Sorting table...")
    rb_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    print ("Creating player tiers...")
    rb_tier_val = player_tiers ("RB", rb_table)

    # Apply marginal value calculation
    print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (rb_table, rb_tier_val, total_marg_val)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(rb_table)
    url.close()

    # WRs ===================================================================================
    print ('\n========== WRs ==========')
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/projections/wr.php"
    url = urllib.request.urlopen(addr)
    print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = MyHTMLParser()
    print ("Parsing HTML...")
    parser.feed(source)

    # Apply stats for each player
    print ("Building WR position table...")
    for player in parser.players:
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

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "WR", "", fpts, cus_fpts, 0.0, 0.0))

    # Apply position table as temporary table sorted on custom fantasy points
    print ("Sorting table...")
    wr_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    print ("Creating player tiers...")
    wr_tier_val = player_tiers ("WR", wr_table)

    # Apply marginal value calculation
    print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (wr_table, wr_tier_val, total_marg_val)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(wr_table)
    url.close()

    # TEs ===================================================================================
    print ('\n========== TEs ==========')
    # Create the URL address and open it with urllib.request. Save the source as a
    # string to be parsed.
    addr = "http://www.fantasypros.com/nfl/projections/te.php"
    url = urllib.request.urlopen(addr)
    print ("Storing HTML source from: " + addr)
    source = str(url.readlines())

    # Create instance of HTML Parser and feed the source file to be parsed
    parser = MyHTMLParser()
    print ("Parsing HTML...")
    parser.feed(source)

    # Apply stats for each player
    print ("Building TE position table...")
    for player in parser.players:
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

        # Build temporary table with Player class objects for position
        tmp_table.append(Player(name, team, "TE", "", fpts, cus_fpts, 0.0, 0.0))

    # Apply position table as temporary table sorted on custom fantasy points
    print ("Sorting table...")
    te_table = sorted(tmp_table, key=lambda player: player.cus_fpts, reverse=True)

    # Apply algorithm for player tiers for position
    print ("Creating player tiers...")
    te_tier_val = player_tiers ("TE", te_table)

    # Apply marginal value calculation
    print ("Assigning marginal value...")
    total_marg_val = assign_marginal_value (te_table, te_tier_val, total_marg_val)

    # Clear temporary table, add position to all-players list, close URL
    tmp_table = []
    all_player_table.extend(te_table)
    url.close()


    # AUCTION VALUES ========================================================================
    print ('\n===== CALCULATIONS ======')
    print ("Total Marginal Value   : " + "%.3f" % total_marg_val)
    marg_pts_per_dollar = total_marg_val / DISCR_MONEY
    print ("Marg. Points Per Dollar: " + "%.3f" % marg_pts_per_dollar)
    print ("Keeper Value Inflation:  " + "%.3f" % KEEPER_INFLATION)

    # Sort all players by marginal value to get value rankings
    print ("Sorting all players by marginal value...")
    tmp_table = all_player_table
    all_player_table = sorted(tmp_table, key=lambda player: player.marg_val, reverse=True)

    # Write column categories to file
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
    print ("Applying auction value, budget percentage, and static inflation...")
    for player in all_player_table:
        # Calculate remaining values
        player.auct_val = math.ceil((player.marg_val / marg_pts_per_dollar) + 1)
        budget_per      = ( player.auct_val / AUCTION_MONEY ) * 100
        inflation       = player.auct_val * KEEPER_INFLATION

        # Write player data to file
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

        if (VERBOSITY > 1):
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
    print ('\n========== END ==========')
    # Close the file
    f.close()

    # Indicate success
    print ("File created: " + OUT_FILE)
    print ("Import into Excel using tab delimiters")

# MAIN ======================================================================================
if __name__ == "__main__":
   main(sys.argv[1:])

