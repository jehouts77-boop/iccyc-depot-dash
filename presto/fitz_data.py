# fitz_data.py - the words of the Edmund Fitzgerald remembrance (screens/fitz.py)
#
# Every statement was checked against a source on 2026-10-07 and approved by
# Jason; the sources are listed card by card in data/fitz/fitzgerald_sources.md.
# Plain ASCII only (the Presto's built-in font). Times are Eastern, as the
# sources give them. Change the wording there first, then here.

TITLE = ("THE EDMUND FITZGERALD", "1958 - 1975")

CARDS = (
    "Launched in June 1958 at River Rouge, Michigan, she was 729 feet long: "
    "the largest ship on the Great Lakes.",
    "She belonged to the Northwestern Mutual Life Insurance Company and was "
    "named for its chairman.",
    "For 17 years she carried taconite, pellets of iron ore, from the Minnesota "
    "iron range to the mills of Detroit and Toledo. Six times she set the record "
    "for a season's haul.",
    "On the afternoon of November 9, 1975, she left Superior, Wisconsin, with "
    "26,116 tons of taconite, bound for a steel mill near Detroit. Captain "
    "Ernest M. McSorley commanded a crew of 28.",
    "The next day a storm crossed Lake Superior with near-hurricane winds. The "
    "freighter Arthur M. Anderson followed ten miles astern.",
    "At 3:30 p.m. McSorley radioed: 'I have a fence rail down, two vents lost "
    "or damaged, and a list.' Later he reported both radars gone.",
    "By evening the Anderson logged winds of 58 knots and seas of 18 to 25 feet.",
    "At 7:10 p.m. McSorley told the Anderson: 'We are holding our own.' Minutes "
    "later the Fitzgerald was gone from the radar. No distress signal was "
    "received.",
    "She lies in two pieces in 530 feet of water, about 17 miles from Whitefish "
    "Bay. All 29 men aboard were lost. None was ever found.",
    "Why she sank has never been settled. The Coast Guard and the NTSB blamed "
    "hatch covers that let the hold flood. The lake carriers believed she had "
    "struck a shoal near Caribou Island.",
    "The day after, the Mariners' Church of Detroit rang its bell 29 times, once "
    "for each man. In 1976 Gordon Lightfoot's song carried the story around the "
    "world.",
    "Her bell was raised on July 4, 1995, and is kept at the Great Lakes "
    "Shipwreck Museum at Whitefish Point. A new bell, engraved with the names of "
    "the crew, rests on the wreck in its place.",
)

# The crew: one toll of the bell for each. Captain first, then by department.
# (name, position, home, age)
CREW = (
    ("Ernest M. McSorley", "Captain", "Toledo, Ohio", 63),
    ("John H. McCarthy", "First Mate", "Bay Village, Ohio", 62),
    ("James A. Pratt", "Second Mate", "Lakewood, Ohio", 44),
    ("Michael E. Armagost", "Third Mate", "Iron River, Wisconsin", 37),
    ("George J. Holl", "Chief Engineer", "Cabot, Pennsylvania", 60),
    ("Edward F. Bindon", "First Assistant Engineer", "Fairport Harbor, Ohio", 47),
    ("Thomas E. Edwards", "Second Assistant Engineer", "Oregon, Ohio", 50),
    ("Russell G. Haskell", "Second Assistant Engineer", "Millbury, Ohio", 40),
    ("Oliver J. Champeau", "Third Assistant Engineer", "Sturgeon Bay, Wisconsin", 41),
    ("Ralph G. Walton", "Oiler", "Fremont, Ohio", 58),
    ("Blaine H. Wilhelm", "Oiler", "Moquah, Wisconsin", 52),
    ("Thomas D. Bentsen", "Oiler", "St. Joseph, Michigan", 23),
    ("Gordon F. MacLellan", "Wiper", "Clearwater, Florida", 30),
    ("Robert C. Rafferty", "Steward", "Toledo, Ohio", 62),
    ("Allen G. Kalmon", "Second Cook", "Washburn, Wisconsin", 43),
    ("Frederick J. Beetcher", "Porter", "Superior, Wisconsin", 56),
    ("Nolan S. Church", "Porter", "Silver Bay, Minnesota", 55),
    ("John D. Simmons", "Wheelsman", "Ashland, Wisconsin", 63),
    ("Eugene W. O'Brien", "Wheelsman", "Toledo, Ohio", 50),
    ("John J. Poviach", "Wheelsman", "Bradenton, Florida", 59),
    ("Ransom E. Cundy", "Watchman", "Superior, Wisconsin", 53),
    ("William J. Spengler", "Watchman", "Toledo, Ohio", 59),
    ("Karl A. Peckol", "Watchman", "Ashtabula, Ohio", 20),
    ("Thomas D. Borgeson", "Maintenance Man", "Duluth, Minnesota", 41),
    ("Joseph W. Mazes", "Special Maintenance Man", "Ashland, Wisconsin", 59),
    ("Mark A. Thomas", "Deck Hand", "Richmond Heights, Ohio", 21),
    ("Paul M. Riippa", "Deck Hand", "Ashtabula, Ohio", 22),
    ("Bruce L. Hudson", "Deck Hand", "North Olmsted, Ohio", 22),
    ("David E. Weiss", "Cadet", "Agoura, California", 22),
)

CLOSING = ("'WE ARE HOLDING OUR OWN.'", "TO THE TWENTY-NINE.")
