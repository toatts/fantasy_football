# HEADER ====================================================================================
# File   : config.py
# Version: 0.1
# Summary:
# Input specific league data into this configuration file. The Python program
# ff_draft_organizer.py uses the information to compile specific draft recommendations
# according to league rules.
#
# (C) Copyright 2014, All Rights Reserved
#
#
# LEAGUE INFO ===============================================================================
teams =                 12      # Teams in the fantasy league
auction_money =         220     # Money alloted to each team for an auction draft
roster_slots =          17      # Roster slots available per team (total)

# SCORING ===================================================================================
pass_completion =       0.05    # Points per pass completion (QB)
passing_yard =          0.04    # Points per passing yard (QB)
passing_touchdown =     4.0     # Points per passing touchdown (QB)
interception =          -3.0    # Points per interception thrown (QB)
rushing_attempt =       0.1     # Points per rushing attempt (RB/WR)
rushing_yard =          0.1     # Points per rushing yard (RB/WR)
rushing_touchdown =     6.0     # Points per rushing touchdown (RB/WR)
reception =             1.0     # Points per reception (RB/WR/TE)
receiving_yard =        0.1     # Points per receiving yard (RB/WR/TE)
receiving_touchdown =   6.0     # Points per receiving touchdown (RB/WR/TE)
fumble =                -2.0    # Points per fumble

# MARGINAL SCORING ==========================================================================
expected_drafted_qbs =  2.25    # Expected amount quarterbacks drafted per team
expected_drafted_rbs =  5.0     # Expected amount of running backs drafted per team
expected_drafted_wrs =  5.0     # Expected amount of wide receivers drafted per team
expected_drafted_tes =  1.68    # Expected amount of tight ends drafted per team
# Starting positions available per position (for Flex, divide by total options for position)
starting_qbs         =  1.0     # Max number of starting QBs per team
starting_rbs         =  2.83    # Max number of starting RBs per team
starting_wrs         =  2.83    # Max number of starting WRs per team
starting_tes         =  1.33    # Max number of starting TEs per team

# KEEPERS ===================================================================================
keeper_money_used =     0       # Total amount of auction money used towards keepers
keeper_value =          0       # Total amount of monetary value absorbed by keepers

