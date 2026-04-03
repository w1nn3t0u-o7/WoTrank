# TODO

- [ ] discover how to host api and frontend on my home server
- [ ] check potential problem with the differing timezone for dates from the replay files and the match hours

## Parser

- [x] Add information about Onslaught format to the tournament besides 7v7
- [x] Add server field besides location that will derive info from location
- [x] Add function that will populate matches, teams and players tables
- [x] deal with different languages map names
- [ ] Add function for filling in vehicles table
- [ ] add colors to the logs for better readability
- [ ] learn about alembic to avoid dropping tables with data if table models are changed
- [ ] deal with the differing replay nicknames and liquipedia data
    - [ ] 2 names are cant be currently matched by fuzzy matcher
    - [ ] add a possibility to add player entry based off of replay performance if a player is not listed on liquipedia tournament page
- [ ] Add MVP column to the tournaments table extracted from the placements or find a different way to extract mvp data

## Web app

- [ ] Fix a bug with different data when sorting by a tournament
- [ ] Fix a bug with sorting by not working
- [ ] Add some styling


