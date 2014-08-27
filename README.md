Fantasy Football Draft Organizer
================================

Summary:
--------
This program scrapes consensus stat projections from
http://www.fantasypros.com/nfl/projections for QBs, RBs, WRs, and TEs. It compiles
stats for each player, applies configurable league point rules, and creates an approximate
total year season point projection. Projections are given marginal value to increase value 
of higher "tier" players. Applies inflation for keeper leagues due to value being 
lost from the player pool. Output is stored to a tab delimited file to import into
spreadsheet software. Optimized for auction leagues, but valid information for snake draft
leagues as well.

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
$ python ff_draft_organizer.py -v [verbosity 0-2] -o [output file] -t [type snake/auction]
```

Changelist:
-----------
###v0.6:
- Fix console display (try to merge with text printout)
- Only display total table on -v 1
- Confirm config.py settings for current year (average last years in)
- Modify usage for snake draft (require command line input to choose which method)

###v0.5:
- Fix name matching issues (remove special characters)
- Use http://www.fantasypros.com/nfl/depth-charts.php for depth chart additions
- Use http://www.cbssports.com/nfl/injuries for injury news 
- Optimize name searching

###v0.4:
- Add quality starts stat from http://www.fantasypros.com/nfl/players/quality-starts.php?position=QB
- Only attempt to create output file if user requests it (default setting for no inputs 
  is verbosity 1 and no output)
- Fix update date and add in projection sources
- Cleanup many duplicate code sections with functions

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
- Test strategy with mock auction draft on test league
- Write data to a database? Update database when new, read in current info otherwise?
