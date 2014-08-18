Fantasy Football Draft Organizer
================================

Summary:
--------
This program scrapes consensus stat projections from
http://www.fantasypros.com/nfl/projections for QBs, RBs, WRs, and TEs. It compiles
stats for each player, applies configurable league point rules, and creates an approximate
total year season point projection. Projections are given marginal value to increase value 
of higher "tier" players. Further applies inflation for keeper leagues due to value being 
lost from the player pool. Output is stored to a tab delimited file to import in a 
spreadsheet for further manipulation. Currently optimized for auction leagues only.

Requirements:
-------------
Python 3.3

Usage:
------
Copy the source to your environment and edit config.py. Input data
for your specific league scoring rules, auction money, keeper prices/value, 
and roster settings.

Run:
----
```       
$ python ff_draft_organizer.py -v [verbosity 0-2] -o [output file]
```

Changelist:
-----------

###v0.3: 
- Updated README to use markdown
- Removed 2013 option to more generic program
- Added config.py for user configurable variables
- Added command line options for verbosity, output file, and help (in progress)

###v0.2: 
- Cleaned up code for reuse
- Added table printouts and verbosity settings
- Created github repo

###v0.1:
- Preliminary mock-up, not stored to github

Future Releases:
----------------
- Only attempt to create output file if user requests it (default setting for no inputs 
  is verbosity 1, no output)
- Add quality starts to list from http://www.fantasypros.com/nfl/players/quality-starts.php?position=QB
- Use http://www.fantasypros.com/nfl/depth-charts.php for depth chart additions
- Use http://www.cbssports.com/nfl/injuries for injury news 
- Modify usage for snake draft (require command line input to choose which method)


