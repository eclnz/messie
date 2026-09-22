"""Fictional personal and domestic documents used as clustering ground truth.

Each topic key maps to six (filename_stem, body_text) pairs drawn from the kind of
folder a person actually keeps: recipes, a half-written novel, trip plans, guitar
tabs, garden notes and so on. Entries inside a topic deliberately reuse the same
concrete nouns and names, because one embedding backend matches literal words
rather than meanings, and a topic whose entries share no vocabulary would not
cluster. Vocabulary is kept apart between topics for the same reason. Everything
here is invented: no real people, addresses, lyrics or published text.
"""

from __future__ import annotations

TOPICS: dict[str, list[tuple[str, str]]] = {
    "baking_recipes": [
        (
            "banana bread (the good one)",
            "Preheat the oven to 180 degrees and grease a loaf tin before you start. Mash "
            "four black bananas into the batter with the melted butter and the brown sugar, "
            "then sift the flour and baking soda over the top and fold gently. Overmixing "
            "the flour makes the crumb tough, so stop while it still looks streaky. Pour the "
            "batter into the tin, scatter a spoon of demerara sugar across the surface and "
            "bake for fifty minutes. A skewer pushed into the centre of the loaf should come "
            "out clean with only a crumb or two clinging to it. Cool the loaf in the tin for "
            "ten minutes, then turn it out onto a wire rack. It slices best the next day, "
            "once the crumb has settled and the butter has firmed up again.",
        ),
        (
            "sourdough_starter_schedule",
            "Feed the starter twice a day with equal weights of flour and water, discarding "
            "all but fifty grams each time. When it doubles reliably in four hours it is "
            "ready to leaven a loaf. Mix five hundred grams of bread flour with water and "
            "let the dough rest for an hour before adding salt. Fold the dough in the bowl "
            "every thirty minutes for three hours, then shape it and let it prove in a "
            "banneton overnight in the fridge. Bake at the hottest setting the oven will "
            "give you, inside a covered pot for twenty minutes, then uncovered for another "
            "twenty until the crust is dark. Cool the loaf completely on a rack before "
            "slicing or the crumb will be gummy and the crust will soften.",
        ),
        (
            "Mum's shortcrust pastry notes",
            "Keep everything cold. Rub cold butter into the flour with your fingertips until "
            "the mixture looks like coarse breadcrumbs, then add iced water a spoon at a "
            "time until the dough just holds together. Do not knead it. Wrap the dough and "
            "rest it in the fridge for half an hour so the flour relaxes and the butter "
            "firms up again. Roll it out on a floured board, line the tin, prick the base "
            "and chill it once more before baking blind with beans at 190 degrees. Twenty "
            "minutes covered, ten minutes uncovered, until the pastry is sandy and pale "
            "gold. The filling goes in afterwards so the base never turns soggy. This makes "
            "enough for one deep tart tin with a little dough left over for jam tarts.",
        ),
        (
            "cinnamon buns - second attempt",
            "The first batch was dry because I baked them too long and used too much flour "
            "in the dough. This time keep the dough slack and sticky. Warm the milk, add the "
            "yeast and sugar, then work in the eggs, butter and flour until it is smooth and "
            "tacky. Prove in a warm place until doubled. Roll the dough into a rectangle, "
            "spread soft butter over it, scatter cinnamon and brown sugar, then roll and cut "
            "twelve buns. Prove again in the tin until they touch. Bake at 180 degrees for "
            "twenty-two minutes only, and brush them with syrup the moment they leave the "
            "oven so the crumb stays soft. Ice them once they are just warm, never hot, or "
            "the icing slides off and pools in the tin.",
        ),
        (
            "lemon drizzle for the school fair",
            "Double quantities for the school fair: this batter fills two loaf tins. Cream "
            "the butter and caster sugar until pale, beat in four eggs one at a time, then "
            "fold in the flour with the zest of three lemons. If the batter curdles add a "
            "spoon of flour and carry on. Bake at 170 degrees for forty-five minutes, "
            "turning the tins once halfway so they colour evenly in our uneven oven. While "
            "the loaves are still hot, prick them all over with a skewer and spoon over "
            "lemon juice mixed with granulated sugar so it soaks into the crumb and sets "
            "crunchy on top. Cool in the tin. Do not attempt to turn them out early because "
            "the drizzle makes the base fragile and it tears.",
        ),
        (
            "brownies_tray_bake_2024",
            "Melt dark chocolate and butter together over a pan of simmering water and let it "
            "cool a little. Whisk the eggs with the sugar until thick and pale, which takes "
            "longer than you think, then fold in the chocolate followed by the flour and "
            "cocoa. That whisking is what gives the shiny crust. Pour the batter into a "
            "lined tray and bake at 175 degrees for exactly twenty-five minutes. The centre "
            "should still wobble; a skewer will not come out clean and that is correct. Cool "
            "the whole tray completely before cutting, ideally in the fridge overnight, or "
            "the brownies will fall apart under the knife. Cut sixteen squares with a hot "
            "knife wiped between each cut. Keeps four days in a tin.",
        ),
    ],
    "novel_manuscript": [
        (
            "chapter_01_draft",
            "Maren Ashgrove came back to Torlin Quay on the last ferry of the season, with "
            "her mother's letter still unopened in her coat pocket. The harbour had not "
            "changed: the same tilted crane, the same gulls arguing over the fish crates, "
            "the same brown light over the water. Halloran was waiting at the end of the "
            "pier because Halloran was always waiting somewhere, and he took her bag without "
            "asking. They walked up the hill to the house on Sennet Row without speaking "
            "about the letter or about the fire or about the eleven years in between. Maren "
            "counted the windows as she climbed. Nine of them dark, one of them lit, and "
            "behind that one her brother Ives was pretending he had not heard the ferry come "
            "in at all.",
        ),
        (
            "chapter_03_draft",
            "Ives had kept the house on Sennet Row exactly as their mother left it, which "
            "Maren decided was a kind of accusation. He made tea in the cracked pot and "
            "talked about the quay, about how Torlin was finished now that the cannery had "
            "closed, about Halloran taking on work he should not take on. Maren let him "
            "talk. Through the window she could see the harbour crane against the evening, "
            "and the gulls moving in loose circles over the water. When she finally asked "
            "about the fire, Ives put the pot down very carefully, the way their father used "
            "to put things down, and said that some questions had answers you could not "
            "return from. Then he went out and did not come back until the tide had turned.",
        ),
        (
            "chapter 07 - the quay scene",
            "The storm came in across Torlin Quay just after midnight and Halloran went down "
            "to the boats alone. Maren followed him because she had spent eleven years not "
            "following anyone and it had earned her nothing. The crane groaned above the "
            "harbour. Rain ran off the fish crates in sheets. Halloran was untying a line "
            "with his back to her and when he turned she saw the burn scar along his "
            "forearm, the one he had never explained, the one that matched the date on her "
            "mother's letter. Somewhere up the hill a window on Sennet Row went dark. The "
            "gulls had gone quiet, which on this coast always meant something was coming "
            "that the birds already understood and the people did not.",
        ),
        (
            "torlin_notes_characters",
            "Maren Ashgrove: thirty-four, left Torlin at twenty-three, works as a surveyor, "
            "reads the harbour like a chart. Ives Ashgrove: older brother, stayed, keeps the "
            "house on Sennet Row, careful with his hands, evasive about the fire. Halloran: "
            "no first name in the book, knew the mother, has the burn scar, does work at the "
            "quay he will not describe. The mother is dead before the novel opens but her "
            "letter drives everything, so do not reveal its contents before chapter eleven. "
            "The cannery closure is the reason the town is emptying. Recurring images to "
            "keep: the tilted crane, the gulls over the fish crates, the nine dark windows, "
            "the ferry that only runs in season. Torlin weather should always be brown "
            "light, rain, or a tide that has just turned.",
        ),
        (
            "chapter_11_rewrite_v2",
            "She opened her mother's letter on the floor of the kitchen at Sennet Row with "
            "the storm still moving off over Torlin Quay. It was four pages and the "
            "handwriting failed halfway down the second. The fire had not been an accident. "
            "Halloran had been in the cannery that night and so had Ives, and their mother "
            "had watched from the harbour and chosen, in the space of about a minute, which "
            "of them she was going to call for. Maren read it twice. Outside the gulls were "
            "coming back over the fish crates, which meant morning. When Ives came down the "
            "stairs she did not hide the pages. She put them on the table facing him and "
            "waited for her brother to say the first true thing in eleven years.",
        ),
        (
            "ending ideas - do not delete",
            "Three possible endings for Torlin. One: Maren stays, takes the house on Sennet "
            "Row from Ives, and the last image is the ferry leaving without her while the "
            "gulls settle on the crane. Two: she burns her mother's letter on the quay and "
            "leaves on the same ferry she arrived on, and Halloran does not come to the pier "
            "this time. Three, which I think is the real one: Ives leaves instead. Maren "
            "watches her brother go down to the harbour with one bag, and she is the one "
            "standing at the end of the pier in the brown light, and the house behind her "
            "has nine dark windows and one lit. Whichever I choose, the scar and the cannery "
            "must be answered by then.",
        ),
    ],
    "travel_itineraries": [
        (
            "Crete trip - hotels",
            "Flights land at Heraklion just after two in the afternoon, so pick up the hire "
            "car at the airport desk rather than in town. Three nights at the small "
            "guesthouse in Chania old town, which has no parking, so leave the car in the "
            "municipal lot by the harbour and walk in with the luggage. Then two nights "
            "further east near Elounda, where the room has a balcony and breakfast is "
            "included until ten. Final night back near the airport because the return flight "
            "boards at six in the morning. Ferry timetables for the island day trip are on "
            "the second page. Confirmation numbers for all four bookings are saved in the "
            "email folder. Check whether the guesthouse wants the passport details in "
            "advance; last time they asked at check-in and it held everyone up.",
        ),
        (
            "japan_2024_day_by_day",
            "Day one: land at Narita, train into the city, drop luggage at the hotel and do "
            "nothing ambitious. Day two to four: city walking, the fish market early, the "
            "garden in the afternoon, temple on the hill before the crowds. Day five: "
            "activate the rail pass at the station counter and take the fast train west, "
            "reserving seats the night before because it is a holiday weekend. Day six to "
            "eight: the old capital, temples in the morning, river walk in the evening, one "
            "day trip by local train. Day nine: coastal stop with the small ryokan, dinner "
            "is served at seven and you cannot be late. Day ten and eleven: back to the city "
            "for shopping and the return flight. Keep the rail pass in the passport wallet, "
            "not the luggage.",
        ),
        (
            "road trip packing + route",
            "Route is roughly six hundred miles over four driving days, so nothing longer "
            "than three hours behind the wheel before a stop. Night one at the lakeside "
            "campsite, which takes bookings only by phone. Night two at the motel off the "
            "highway, cheap and fine, breakfast not included. Night three at the cabin, "
            "which needs a key collected from the village shop before it closes at five, so "
            "leave early that morning. Night four back toward the airport. Packing: one bag "
            "each in the boot, cool box behind the passenger seat, paper map in the door "
            "pocket because the signal disappears for the middle two hundred miles. "
            "Print the campsite booking. Check the hire car excess before we collect it and "
            "photograph the bodywork at the desk.",
        ),
        (
            "lisbon weekend (short)",
            "Friday evening flight lands late, so the hotel knows we are checking in after "
            "eleven and has the code for the door. Saturday: walk the old quarter in the "
            "morning, tram up the hill, long lunch, then the museum which is free after "
            "four. Sunday: the market before it fills up, then the train out along the coast "
            "for the afternoon, back by seven. Monday morning is the return flight, so pack "
            "Sunday night and order the airport taxi for half past six. Two nights only, "
            "hand luggage each, no hire car. Booking references are printed and in the front "
            "pocket of the bag. The guidebook says to buy the transport card at any metro "
            "station rather than at the airport, where the queue is worse.",
        ),
        (
            "iceland ring road plan v3",
            "Ten days clockwise, averaging two hundred kilometres a day, with the hire car "
            "collected at the airport on arrival. Nights one and two in the capital, then "
            "guesthouses booked along the south coast for nights three to five, a farm stay "
            "in the east for nights six and seven, and the north for eight and nine. Final "
            "night near the airport again for the early flight. Check road conditions each "
            "morning before driving because sections close without much warning. Fuel "
            "whenever the tank drops below half; the gaps between stations are long. "
            "Swimming things in the day bag rather than the luggage. All ten bookings are "
            "confirmed by email and the guesthouse in the east wants a phone call the day "
            "before arrival.",
        ),
        (
            "train tickets and transfers.txt",
            "Outbound: local train to the main station at 07:12, then the international "
            "service at 08:40 which arrives just before one. Seat reservations are "
            "compulsory on the second leg and the reference is on the printed ticket, not "
            "the app. Transfer at the destination is a twenty minute walk to the hotel or "
            "one stop on the tram. Return is four days later on the 16:05, changing once "
            "with a fifty minute connection, which is enough but not generous, so sit near "
            "the front of the train. Luggage is one case each plus a day bag. Hotel holds "
            "bags after checkout until five, so the last morning is free for the old town "
            "and lunch near the station before the return leg.",
        ),
    ],
    "guitar_tabs_and_lyrics": [
        (
            "riverlight - verse tab",
            "Capo on the second fret, everything relative to that. Verse runs D, A, Bm, G "
            "with the low string ringing through the change, and the strumming pattern is "
            "down, down-up, up-down-up, kept loose. The hammer-on at the top of the second "
            "bar is the whole hook so do not rush it. Chorus lifts to G, D, A and back, "
            "same pattern but harder on the downstroke. Bridge drops to a single picked line "
            "on the fourth and third strings, frets two and four, played twice before the "
            "last chorus. Vocal sits comfortably in this key; without the capo it is too low "
            "and the chorus loses the strain that makes it work. Solo, if there is one, "
            "stays in the pentatonic shape starting at the fifth fret.",
        ),
        (
            "Setlist - open mic march",
            "Six songs, thirty minutes, capo changes planned so I am not fumbling between "
            "them. Open with Riverlight because the strumming is easy and it settles my "
            "hands. Then Ash And Copper, capo stays on two, straight into it. Third is the "
            "slow one in drop D, so tune the low string down while talking, and remember the "
            "picking pattern is thumb on the bass string throughout. Fourth is a cover, same "
            "chords as the second song, capo off. Fifth is the new one with the tricky "
            "bridge, play it fourth if my hands are cold. Close with the loud one, all "
            "downstrokes, G, D, A, and let the last chord ring out rather than cutting it. "
            "Spare strings and a spare capo in the case.",
        ),
        (
            "ash and copper - lyrics draft",
            "Verse one is written and scans properly over the D to Bm change. Verse two "
            "still has a line too many so the vocal crowds the bar before the chorus; cut "
            "the third line or move the last word into the next bar. Chorus lyric is fine "
            "and lands on the G. Bridge lyric is a placeholder and needs rewriting once the "
            "picked line is settled. Try singing the whole thing a tone lower without the "
            "capo and see whether the chorus still carries. Rhyme scheme is loose and I want "
            "to keep it loose. Keep the repeated line at the end of each chorus because it "
            "gives the audience something to hold on to when the strumming drops out for "
            "two bars before the last verse.",
        ),
        (
            "fingerpicking_exercises",
            "Twenty minutes a day. Start with thumb alternating between the sixth and fourth "
            "strings at sixty beats per minute, no chord changes, just the bass. Then add "
            "the index on the third string and the middle on the second, keeping the thumb "
            "steady. Once that is clean, move it over a chord progression: G, Em, C, D, four "
            "bars each, no capo. The point is that the thumb never changes pattern even when "
            "the fingers do. Then the travis pattern over the same chords, slowly, and only "
            "raise the tempo when a full minute passes without a buzz. Finish with the "
            "picked bridge line from Riverlight at half speed. Fret hand stays curled, wrist "
            "straight, and stop entirely if the tendon on the left hand aches.",
        ),
        (
            "chord chart drop d stuff",
            "Tune the low string down to D. The whole point is the ringing bass, so the "
            "shapes are simple: one finger barring the bottom three strings gives you the "
            "power chords, and the open position D sounds enormous. Progression for the slow "
            "song is D, C, G, D with the low string ringing through every change. Strumming "
            "stays soft on the verse and opens up on the chorus, all downstrokes. Capo does "
            "not work well in this tuning so play it straight. Retune by ear against the "
            "fourth string rather than the tuner if the room is noisy. Write the new bridge "
            "in this tuning too; the picked line on the third and second strings sounds "
            "better here than it did in standard.",
        ),
        (
            "new song ideas 2024-06",
            "Three fragments worth keeping. First: a chorus lyric with no verse yet, sits "
            "over G, D, Em, C, capo on three, strumming heavy. Second: a picked line in drop "
            "D that I keep playing and never finish, thumb on the low string, melody on the "
            "second, probably an instrumental. Third: a verse lyric that scans like Ash And "
            "Copper and may just be the same song again, so check the chords before writing "
            "more. Record all three roughly on the phone before I forget the tempo. The "
            "second one needs a bridge that leaves the tuning alone, and the first needs a "
            "verse that does not repeat the chorus chords or the whole thing will sound flat "
            "by the second minute.",
        ),
    ],
    "garden_planting_notes": [
        (
            "seed sowing 2024",
            "Tomatoes and chillies sown indoors on the windowsill in early March, in module "
            "trays of peat-free compost, kept just moist. Germination was patchy with the "
            "chillies; the tomato seedlings were up in eight days. Prick out into individual "
            "pots once the first true leaves appear and keep them cool so they do not get "
            "leggy. Beans and courgettes go in pots in April, direct sow outdoors only after "
            "the last frost. Carrots and beetroot direct sown in the raised bed, thinned "
            "hard, and the carrot row covered with fleece against the root fly. Salad "
            "sown every fortnight in the shady bed so it does not bolt. Label everything in "
            "pencil; the marker pen faded completely in the greenhouse again last summer.",
        ),
        (
            "Allotment plot - bed rotation",
            "Four beds on a four year rotation. Bed one takes the potatoes this year, "
            "manured over winter and earthed up twice. Bed two takes the legumes, so peas "
            "and the climbing beans up the hazel poles, and the roots are left in the soil "
            "after the haulm is cut for the nitrogen. Bed three takes the brassicas after "
            "the beans, limed and netted against pigeons and cabbage white. Bed four takes "
            "roots: carrots, parsnips, beetroot, no manure or the parsnips fork. Compost "
            "goes on whichever bed is about to take the potatoes. The perennial bed with the "
            "rhubarb and the raspberry canes stays where it is and only gets mulched. Write "
            "next year's plan in October while I can still remember what did badly.",
        ),
        (
            "what died and why (honest list)",
            "The courgettes drowned. Too much watering in a heavy clay soil in a wet July "
            "and the stems rotted at the base. The chillies never ripened because the "
            "greenhouse got no sun after the neighbour's tree filled out. Slugs took the "
            "entire first sowing of lettuce seedlings overnight, so next year sow in modules "
            "and plant out bigger. The parsnips forked badly in the manured bed, which is my "
            "fault for ignoring the rotation. Blight hit the outdoor tomatoes in August, as "
            "it does every year, so grow only blight-resistant varieties outdoors from now "
            "on. Good things: the beans cropped for six weeks, the raspberry canes were the "
            "best yet, and the rhubarb needs dividing because the crown has got enormous.",
        ),
        (
            "compost_and_mulch_notes",
            "Two bays. Fill one over the year with kitchen scraps, grass clippings, shredded "
            "cardboard and spent compost from the pots, turning it into the second bay in "
            "autumn. Keep the ratio of green to brown roughly even or it goes slimy. Do not "
            "add perennial weed roots or seed heads because the heap never gets hot enough "
            "to kill them. The turned heap is usable by spring and goes on the beds as a "
            "mulch rather than being dug in; the worms take it down themselves and the soil "
            "structure on the clay has improved noticeably. Leaf mould in the wire cage "
            "separately, two years to rot, used for potting compost. Mulch the raspberry "
            "canes and the rhubarb crown thickly every March.",
        ),
        (
            "front border planting list",
            "Shady, dry under the hedge, so nothing thirsty. Hardy geraniums along the front "
            "because they fill gaps and flower for months. Hellebores at the back for "
            "winter, epimedium under the hedge itself where nothing else will grow. Three "
            "ferns in the damp corner by the downpipe. Bulbs in autumn: snowdrops in the "
            "green rather than dry, daffodils in drifts of nine, and alliums through the "
            "geraniums for June. Mulch the whole border after planting and water everything "
            "in properly for the first summer even though it is meant to be a dry border. "
            "Cut the geraniums back hard in July and they flower again. No annuals here, the "
            "soil is too poor and the hedge takes all the moisture.",
        ),
        (
            "greenhouse jobs monthly",
            "February: wash the glass, clean the staging, sow the first tomatoes and "
            "chillies in modules with gentle bottom heat. March: pot on the seedlings, sow "
            "salad, start ventilating on warm days. April: harden off anything destined for "
            "outdoors, keep the door open in the day. May: plant the tomatoes into their "
            "final pots, put up the strings, begin feeding weekly. June to August: water "
            "daily, damp down the floor in heat, pinch out side shoots on the tomatoes, "
            "shade the roof. September: last feed, stop pinching, ripen what is left. "
            "October: clear the spent plants to the compost, sweep out, sow overwintering "
            "salad in modules. Check for red spider mite whenever it is dry and hot.",
        ),
    ],
    "house_renovation": [
        (
            "kitchen quotes comparison",
            "Three builders quoted for the kitchen. The first is the cheapest but excludes "
            "plastering and the electrical first fix, which we would then have to arrange "
            "separately, so it is not really cheaper. The second includes everything except "
            "the worktop template and fitting, has a start date in eight weeks, and the "
            "references checked out. The third is highest and wants a forty per cent deposit "
            "up front, which the others do not. All three assume the existing soil pipe stays "
            "where it is. None of them priced removing the chimney breast, so that needs a "
            "structural engineer's calculation first and a separate price. Ask each of them "
            "whether the quote includes making good after the plumber, skip hire, and "
            "whether waste removal is daily or at the end of the job.",
        ),
        (
            "bathroom_rip_out_schedule",
            "Week one: isolate the water, strip out the old suite, remove tiles back to the "
            "brickwork and take up the floor. Expect rot under the bath where the seal has "
            "failed. Week two: plumber moves the soil connection and first fixes the new "
            "pipework, electrician runs the cable for the extractor and the shaver socket. "
            "Week three: plasterboard and skim the walls, tank the shower area properly, lay "
            "the new floor. Week four: tiling, then the suite is fitted and connected, and "
            "the extractor goes in last. Allow a week after that before decorating so the "
            "plaster dries. We have no second bathroom so the toilet must be reconnected at "
            "the end of every working day, which needs agreeing with the plumber in advance.",
        ),
        (
            "damp survey - my notes",
            "Surveyor said the staining on the north wall is not rising damp but penetrating "
            "damp from a failed pointing joint and a blocked gutter above it. Cheaper than "
            "feared. Actions: clear the gutter, repoint about two square metres of "
            "brickwork in a lime mortar rather than cement so the wall can breathe, then "
            "leave it a full winter before replastering inside. The internal plaster is "
            "blown in a patch about a metre wide and will need hacking off back to the brick "
            "and replastering. He also flagged the cement render on the side elevation as a "
            "longer term problem because it traps moisture behind it. No damp proof course "
            "injection needed, which two of the previous firms had quoted for and charged "
            "handsomely to install.",
        ),
        (
            "Loft conversion - building regs questions",
            "Questions for the architect before we submit. Head height at the ridge is only "
            "just adequate, so confirm the floor build-up depth and whether the new joists "
            "can sit alongside the existing ceiling joists rather than above them. Staircase "
            "position and the protected escape route through the landing: does the existing "
            "stairwell need fire doors on every room off it? Insulation between and under "
            "the rafters, and how that affects the ventilation gap at the eaves. Dormer or "
            "rooflights, and whether a dormer on the rear elevation falls inside permitted "
            "development. Steel beam sizes over the party wall and whether that triggers a "
            "party wall agreement with next door. Also confirm the building control route: "
            "local authority or an approved inspector.",
        ),
        (
            "shopping list ikea",
            "For the renovation, not the fun stuff. Two flat pack wardrobes for the back "
            "bedroom once the plastering is finished and dry. Kitchen drawer inserts, the "
            "deep ones. Handles, forty of them, because the builder is supplying the units "
            "without handles. Extendable curtain poles for three windows, plus brackets that "
            "will actually hold in the new plasterboard rather than crumbling out. Dust "
            "sheets and masking tape for the decorating. LED strip for under the wall units "
            "and a driver to match. Measure the alcove beside the chimney breast before "
            "going because the shelving unit comes in two widths and the wrong one will not "
            "fit once the plaster is on. Take the van, not the car.",
        ),
        (
            "budget_tracker_renovation.csv",
            "Running total against the original budget, which we have already exceeded by "
            "about eleven per cent. Biggest overruns: the rewire, because the existing "
            "cabling was worse than the electrician expected and the whole ground floor "
            "needed doing rather than half; and the floor structure in the bathroom, which "
            "was rotten under the bath as predicted but over a bigger area. Savings: we kept "
            "the existing radiators, did the stripping out ourselves, and sourced the tiles "
            "from a clearance lot. Still to come: plastering the hallway, the loft "
            "insulation, decorating throughout, and the contingency we have not touched for "
            "the chimney breast. Keep every invoice for the builder's VAT and log the "
            "deposits paid separately from the staged payments.",
        ),
    ],
    "fitness_training_log": [
        (
            "half marathon plan week 1-4",
            "Four runs a week building to thirteen miles. Monday rest. Tuesday intervals: "
            "warm up a mile easy, then six times three minutes hard with ninety seconds "
            "jogging between, cool down a mile. Wednesday rest or easy swim. Thursday steady "
            "five miles at a pace where I can still talk. Friday rest. Saturday easy three "
            "miles plus strides. Sunday long run, starting at seven miles and adding one "
            "mile a week, run slowly, heart rate under one fifty. Week four is a cutback "
            "week: long run drops back to six. Stretch the calves after every run and roll "
            "the left hamstring, which tightened up badly in the spring. Log the pace and "
            "how the legs felt, not just the distance.",
        ),
        (
            "gym_log_squats_deadlift",
            "Squats: worked up to five sets of five at eighty-five kilos, last set was a "
            "grind and the depth got shallow on rep four, so hold this weight another week "
            "before adding. Deadlift: three sets of five at a hundred and ten, bar speed "
            "fine, grip failing on the last rep so start using the mixed grip on the top "
            "set. Bench: five sets of five at sixty, easy, add two and a half next session. "
            "Accessories: rows, three sets of eight, and hanging leg raises to finish. Rest "
            "three minutes between the heavy sets. Warm up properly, two empty bar sets and "
            "three ramping sets before the work weight. Left knee fine this week; the taping "
            "seems to help on the heavier squat sessions.",
        ),
        (
            "swim sets - tuesday mornings",
            "Two thousand metres in the hour. Warm up four hundred easy freestyle, then two "
            "hundred kick with the board and two hundred pull with the buoy. Main set is "
            "eight times one hundred on a fixed interval, holding the same pace across all "
            "eight, with twenty seconds rest. Then four times fifty sprint with plenty of "
            "rest, working on the catch rather than thrashing. Cool down two hundred easy. "
            "Breathing every three strokes throughout the main set even when it feels hard, "
            "because my stroke goes lopsided when I breathe to one side only. Shoulders felt "
            "good this week. Count the strokes per length on the easy sections and try to "
            "keep it under eighteen without slowing the pace down.",
        ),
        (
            "injury notes physio hamstring",
            "Physio says the left hamstring tightness is coming from weak glutes rather than "
            "the hamstring itself, so the running load is not the direct cause but it is "
            "exposing it. Exercises three times a week: single leg bridges, three sets of "
            "twelve each side, slow; banded side steps, three sets of fifteen; and single "
            "leg deadlifts with a light dumbbell, three sets of eight, focusing on balance "
            "rather than weight. Stop any run at the first sign of a pull rather than "
            "running through it. Keep the long run easy and drop the intervals for two weeks "
            "before reintroducing them. Stretch after, not before. Review in four weeks and "
            "bring the training log so she can see the weekly mileage.",
        ),
        (
            "Weekly mileage and resting HR",
            "Logging weekly mileage against resting heart rate first thing in the morning. "
            "Weeks one to four averaged twenty-two miles with resting heart rate around "
            "fifty-two. Week five the mileage went to twenty-eight and the resting rate "
            "climbed to fifty-eight, which is the pattern I should have spotted last year: "
            "when it stays elevated three mornings running, the legs are not recovering and "
            "the pace on the steady run drifts slower for the same effort. Cutback week "
            "brought it back down to fifty-one. Sleep is the other variable and I am not "
            "tracking it honestly. Plan: keep the long run, cut one interval session in any "
            "week where the resting rate is up, and do not add mileage and intensity "
            "together.",
        ),
        (
            "bodyweight routine (no gym week)",
            "For weeks away from the gym. Circuit of five exercises, four rounds, minimal "
            "rest within a round and two minutes between rounds. Press-ups, as many good "
            "reps as possible, stopping two short of failure. Split squats, twelve each leg, "
            "slow on the way down. Inverted rows under a table or a low bar, ten reps. "
            "Single leg bridges, twelve each side, which doubles as the physio work. Plank "
            "for a minute, then a side plank each side for thirty seconds. Finish with ten "
            "minutes of easy skipping or a short run if there is anywhere to run. Keeps "
            "enough strength to come back to the squat and deadlift numbers without losing "
            "three weeks of progress.",
        ),
    ],
    "book_club_notes": [
        (
            "book club march - The Salt Register",
            "Eight of us, six had finished it. General view: the first hundred pages are "
            "slow and two people nearly gave up before the narrator's sister appears. "
            "Everyone agreed the unreliable narration is handled well, though there was a "
            "long argument about whether the final chapter cheats by withholding the "
            "diagnosis. Discussion questions that worked: whose account do you actually "
            "believe, and does the structure justify the ending, and would the novel survive "
            "being told in the third person. The prose divided the room; two found it "
            "mannered and two thought it was the best writing we have read all year. Average "
            "rating around three and a half. Next month's pick is the translated one, "
            "copies from the library, meeting at the usual time.",
        ),
        (
            "reading list 2024 (voted)",
            "Voted at the December meeting, two rounds, top twelve win. January: the short "
            "debut everyone has already read half of. February: the doorstop nineteenth "
            "century one, which we are splitting over two months because nobody will finish "
            "it otherwise. April: nonfiction, the one about cartography. May: the translated "
            "novel, chosen partly because the library has eight copies. June: short stories, "
            "because summer. September: the prize shortlist title. November: reader's choice, "
            "host picks. Rules we agreed again: no rereads of anything we did in the last "
            "three years, the host chooses the discussion questions, and anyone who "
            "nominates a book over five hundred pages has to lead the discussion for it. "
            "Ratings recorded out of five at the end of each meeting.",
        ),
        (
            "discussion questions - translated novel",
            "Eight questions for Thursday. One: how much does the translator's voice shape "
            "what we think of the prose, and did anyone compare the two available "
            "translations? Two: the narrator never names the city, so what does that "
            "withholding do? Three: the mother's chapters are in the present tense and the "
            "daughter's in the past; is that structure earning its keep? Four: is the "
            "central betrayal believable given what we know of the character by chapter six? "
            "Five: the ending. Six: does the novel expect knowledge of the historical "
            "background it never explains, and does that matter? Seven: who would you "
            "recommend it to. Eight: rating out of five and would you read the author's next "
            "one. Bring your own questions too.",
        ),
        (
            "notes_on_the_doorstop_novel_part2",
            "Second half, chapters twenty-six to the end. Plot finally moves. The subplot "
            "with the lawyer pays off, which justifies the two hundred pages of setup that "
            "half the group complained about in part one. Themes to raise: inheritance and "
            "obligation, the way every character is defined by money they did not earn, and "
            "the narrator's increasing absence from his own story. The prose is genuinely "
            "funny in places, which surprised the people who had bounced off it. Weak point "
            "is the ending, which resolves three marriages in four pages. Ratings: those who "
            "finished it rated it four or five, those who did not finish rated it two, which "
            "tells its own story about long novels in a book club with a monthly meeting.",
        ),
        (
            "who hosts when",
            "Rotation for the year, second Thursday of the month, eight o'clock, six to ten "
            "people. The host provides somewhere to sit and leads the discussion with their "
            "own questions, and everyone else brings something. Whoever nominated the book "
            "leads if they are not hosting. If the host cannot make it, swap rather than "
            "cancel, because cancelling once means we lose two months. Library copies need "
            "ordering six weeks ahead for anything popular, so the host for a given month "
            "should confirm the title at the previous meeting. Ratings sheet lives with "
            "whoever hosted last. December is the voting meeting for next year's reading "
            "list and nobody has to have read anything.",
        ),
        (
            "books i bailed on and why",
            "Personal list, not for the group. The prize winner from two years ago: "
            "beautiful prose, no narrative pull, stopped at page ninety and felt no urge to "
            "return. The thriller everyone recommended: the reveal was obvious by chapter "
            "four. The nonfiction one about cartography: genuinely good but I read it too "
            "slowly and the library wanted it back. The debut novel: the narrator was doing "
            "a voice I could not stand for three hundred pages. Pattern I notice is that I "
            "abandon books for voice far more often than for plot, and that I finish almost "
            "everything the group picks because the meeting is a deadline. Rating things out "
            "of five has made me a harsher and probably worse reader.",
        ),
    ],
    "wedding_planning": [
        (
            "guest list v6 FINAL (not final)",
            "One hundred and four for the ceremony and the sit-down meal, another thirty "
            "joining in the evening. The venue caps the dining room at one hundred and ten, "
            "so there is no room left for the maybes. Split roughly evenly between the two "
            "families, which took some doing. Plus ones for anyone in a long relationship, "
            "not for everybody, and we are holding that line. Children: eleven of them, all "
            "family, seated together near the door with the activity bags. Dietary "
            "requirements collected with the RSVPs: six vegetarian, two vegan, three gluten "
            "free and one nut allergy that the caterer needs telling about directly rather "
            "than on the form. Evening-only invitations go out six weeks before, after the "
            "main RSVP deadline has passed.",
        ),
        (
            "Venue and catering - questions to ask",
            "For the viewing. Is the ceremony room licensed and how long does the turnaround "
            "take before the meal. What time does the bar have to close and is there a "
            "corkage fee if we bring our own wine. Does the price include the chairs, the "
            "linen and the cake stand or are those hired separately. How late can the band "
            "play and is there a noise limiter in the room. Do they provide a coordinator on "
            "the day or only up to the day. Menu tasting: when, and how many of us can come. "
            "Confetti allowed outside? Parking for a hundred cars and is there anywhere for "
            "the camper van. Deposit, balance date, and exactly what the cancellation terms "
            "say in writing.",
        ),
        (
            "order of the day timings",
            "Ceremony at one, so guests arrive from half past twelve and the registrar wants "
            "to see us both separately at noon. Drinks reception and photographs from half "
            "past one to three in the walled garden, with the group photographs listed on a "
            "separate sheet so the photographer is not hunting for people. Guests called to "
            "sit at quarter past three, meal served at half past. Speeches after the main "
            "course, not before, three of them, ten minutes each maximum and I have told "
            "them all. Room turnaround from five while everyone is outside. Cake cut at "
            "seven, first dance at half past, evening food at nine, bar closes at midnight "
            "and the band finishes at half past eleven.",
        ),
        (
            "invitation wording drafts",
            "Three versions. The formal one, with both sets of parents named at the top, "
            "which one side wants and the other finds stiff. The middle one, issued in our "
            "own names, warmer, with the parents thanked on the back. The casual one, which "
            "reads well but does not make clear that there is a sit-down meal and that the "
            "dress code is not jeans. Going with the middle version. Details to include: "
            "date, ceremony time, venue name and address, RSVP by the deadline with an email "
            "address, dietary requirements, the accommodation list, and a line about the gift "
            "list that does not sound like a demand. Evening invitations use the same design "
            "with different wording and a later arrival time.",
        ),
        (
            "budget spreadsheet notes",
            "Venue hire and catering together are just over half the total, which is "
            "apparently normal. Second biggest is the photographer, then the band, then the "
            "dress and the suits. Flowers came down a lot by using what is in season and "
            "reusing the ceremony arrangements on the tables afterwards. Still unbudgeted: "
            "the registrar's fee, the cake, transport for both families between the hotel "
            "and the venue, and the favours we probably will not bother with. Deposits paid "
            "so far: venue, photographer, band. Balances all fall due in the month before, "
            "which is going to be an unpleasant few weeks. Keep about eight per cent back as "
            "contingency because everyone says something unbudgeted arrives in the final "
            "fortnight.",
        ),
        (
            "seating_plan_attempt_4",
            "Twelve round tables of eight to ten. Top table is just the two of us and the "
            "wedding party, which avoids the entire parents question. Table one and two are "
            "one family, three and four the other, five and six are university friends, "
            "seven and eight are work, nine and ten are the neighbours and the older "
            "relatives near the door and away from the band speakers. Eleven is the "
            "children plus two tolerant adults. Twelve is the difficult table and I have "
            "spent four evenings on it. Constraints: the two who do not speak cannot see "
            "each other, the one who talks over everyone goes with the ones who will talk "
            "back, and nobody sits alone without at least one person they know.",
        ),
    ],
    "car_maintenance": [
        (
            "service history + mileage",
            "Bought at forty-one thousand miles with a full stamped history. Major service "
            "at fifty thousand: oil and filter, air filter, pollen filter, spark plugs, "
            "brake fluid changed. Cambelt and water pump done at sixty-two thousand, which "
            "is the big one out of the way, invoice filed with the handbook. Interim "
            "services every ten thousand miles or twelve months, oil and filter only. "
            "Currently on seventy-eight thousand and the next interim is due. Tyres: fronts "
            "replaced at seventy-one thousand, rears original and down to about four "
            "millimetres of tread, so they will need doing before winter. Battery is five "
            "years old and slow to turn over on cold mornings. Keep every invoice; the "
            "stamped book alone is worth money at resale.",
        ),
        (
            "MOT advisories 2024",
            "Passed, but four advisories. One: nearside rear tyre close to the legal tread "
            "limit, which matches what I already knew, so both rears get replaced. Two: "
            "slight play in the offside front drop link, not a fail yet but it explains the "
            "knocking over speed bumps, and a pair of drop links is cheap. Three: minor oil "
            "weep from the sump gasket, monitor it and keep checking the dipstick monthly. "
            "Four: front brake discs lipped and pads at about three millimetres, so discs "
            "and pads front axle before the next test. Exhaust noted as corroded at the rear "
            "box but not blowing. Get the drop links and the brakes done together to save a "
            "second lot of labour.",
        ),
        (
            "oil change notes (what fits)",
            "Takes four and a half litres of fully synthetic to the correct specification; "
            "check the handbook rather than trusting the shop's lookup, which gave the wrong "
            "grade last time. Oil filter is the cartridge type in the housing on top of the "
            "engine, not a spin-on, so it needs the special socket that lives in the toolbox. "
            "Sump plug takes a new crush washer every time. Drain it warm but not hot, let "
            "it drip for twenty minutes, torque the plug properly rather than guessing. "
            "Refill with four litres, run it, check the dipstick, then add the rest slowly to "
            "the upper mark. Reset the service light through the menu on the dash. Take the "
            "old oil to the tip; they have a waste oil tank.",
        ),
        (
            "winter checks and tyres",
            "Before the cold sets in. Tread depth all round with the gauge, not the coin: "
            "anything under three millimetres gets replaced now rather than in February. "
            "Pressures checked cold, including the spare, which was flat last time I looked. "
            "Battery tested at the garage because it is five years old and cranks slowly; if "
            "the voltage drops under load, replace it rather than waiting to be stranded. "
            "Coolant strength tested with the hydrometer, topped up with the correct "
            "antifreeze mix. Screenwash to the winter concentration, not summer. Wiper blades "
            "replaced, both, they smear badly. Check all the bulbs including the number "
            "plate light, which is the one that gets picked up. Scraper and a blanket in the "
            "boot.",
        ),
        (
            "that rattle - diagnosis attempts",
            "Metallic rattle from the front, only over rough surfaces, not under braking and "
            "not related to engine speed, so probably suspension rather than exhaust. First "
            "attempt: checked the heat shields, one was loose and I clamped it, rattle "
            "continued. Second: jacked the front up and levered at the anti-roll bar drop "
            "links, and there is clear play in the offside one, which matches the MOT "
            "advisory. Third: checked the top mounts by turning the wheel lock to lock with "
            "the weight on, no knocking from there. Conclusion is the drop links. Pair of "
            "them plus an hour of labour, or do it myself with the axle stands if the ball "
            "joints are not seized into the strut. Brake discs due anyway.",
        ),
        (
            "insurance_and_tax_renewal",
            "Insurance renews in March and the automatic quote came back nearly a hundred "
            "pounds higher than last year with no claims and another year of no claims "
            "bonus, which is the usual trick. Rang them, quoted two cheaper renewal prices "
            "from the comparison sites, and they matched it within ten pounds. Mileage "
            "declared is fine at eight thousand a year. Voluntary excess kept where it is. "
            "Breakdown cover is separate and renews in July; check whether the policy covers "
            "home start and a tow, because the cheap tier does not. Road tax is monthly by "
            "direct debit. MOT falls due in October, which is worth booking early so any "
            "advisories can be fixed before the test rather than after it.",
        ),
    ],
    "language_learning_notes": [
        (
            "spanish verbs - preterite vs imperfect",
            "The distinction is not about how long something lasted but about how the "
            "speaker frames it. Preterite for a completed action seen as a whole event: it "
            "happened, it finished, it moves the story forward. Imperfect for background, "
            "description, habitual actions and states that were ongoing when something else "
            "interrupted. Typical pairing: imperfect sets the scene, preterite breaks it. "
            "Time expressions are a useful clue but not a rule: siempre and todos los días "
            "usually take the imperfect, ayer and de repente usually the preterite. Verbs "
            "that change meaning between the two tenses need memorising separately: knowing "
            "versus finding out, wanting versus trying, being able versus managing to. Drill "
            "these with short narrative paragraphs rather than isolated conjugation tables.",
        ),
        (
            "vocab list - kitchen and food",
            "Nouns with their gender written in, because getting the article wrong is the "
            "mistake I make most. Thirty-two words this week grouped by where they live in "
            "the kitchen rather than alphabetically, which makes them stick better. Verbs to "
            "go with them: to chop, to boil, to fry, to taste, to serve, all with their "
            "irregular stems noted. Three useful phrases for ordering and three for a market "
            "stall. Review schedule: same day, next day, then three days, then a week, then a "
            "month, in the flashcard app. Words that failed the review twice get written into "
            "a sentence by hand, which is slower but works. Do not add more than thirty new "
            "words in a week or the reviews pile up and I stop doing them.",
        ),
        (
            "italki lesson notes 12 may",
            "Fifty minutes, mostly conversation about the weekend, tutor correcting only "
            "errors that blocked understanding and noting the rest for the end. Corrections: "
            "the subjunctive after expressions of doubt, which I avoid entirely by "
            "rephrasing; the wrong past tense in three narrative sentences, same preterite "
            "and imperfect problem; and the preposition after two common verbs. Fluency was "
            "better than last month but I fall back on the same four connecting phrases. "
            "Homework: write two hundred words narrating a past weekend using both past "
            "tenses deliberately, and record myself reading it aloud. Tutor recommended "
            "listening to one podcast episode twice, once for gist and once with the "
            "transcript, rather than four different episodes once each.",
        ),
        (
            "grammar_notes_subjunctive",
            "Triggered by the speaker's attitude, not by the fact itself. Wanting, hoping, "
            "doubting, denying, and impersonal expressions of opinion all take it in the "
            "subordinate clause when the subject changes; when the subject is the same you "
            "use the infinitive instead, which removes about half the cases. After "
            "conjunctions of purpose and before an unrealised future event it is obligatory. "
            "After expressions of certainty it is not used, and negating that certainty "
            "flips it back. Present subjunctive forms come from the first person singular "
            "present stem, which makes the irregulars predictable once you know that. Drill "
            "the triggers as whole phrases rather than as a list of rules, because in speech "
            "there is no time to work through a decision tree.",
        ),
        (
            "listening practice log",
            "Twenty minutes daily. Podcast for learners at a slower pace three days a week, "
            "native-speed radio two days, and one film episode at the weekend with "
            "subtitles in the target language, never in English. Comprehension estimate "
            "written down each time as a rough percentage so I can see it move. Started "
            "around forty per cent on the native-speed material and it is now maybe sixty on "
            "familiar topics, much lower on anything regional or fast. New words heard rather "
            "than read go into the vocab list only if they come up twice. The big gain this "
            "month came from listening to the same episode twice instead of always reaching "
            "for something new, exactly as the tutor said it would.",
        ),
        (
            "phrases to actually use (not textbook)",
            "Things people say that no course taught me. Four fillers for buying thinking "
            "time, which stop me freezing mid-sentence. Two ways of agreeing that are not "
            "the textbook one. The polite hedge before disagreeing. How to ask someone to "
            "repeat themselves slower without sounding like a beginner, and how to ask what "
            "a word means in the target language rather than switching to English. The "
            "casual way of saying you are not sure. Two set phrases for ending a "
            "conversation politely. All of these are worth more per minute of study than "
            "another thirty nouns, because they carry across every conversation. Practise "
            "them aloud until they come out without thought, then they free up attention for "
            "the grammar.",
        ),
    ],
    "birdwatching_journal": [
        (
            "2024-04-13 estuary walk",
            "Out at the estuary hide from half six, tide rising, light overcast with a cold "
            "easterly. Waders pushed steadily up the mud as the water came in. Counted around "
            "two hundred dunlin, forty knot among them, nine grey plover still in winter "
            "plumage and a single bar-tailed godwit already going rusty. Curlew calling "
            "constantly from the saltmarsh, at least fifteen. Two little egret on the far "
            "channel. Best bird was a spotted redshank, picked out on the call before I saw "
            "it, feeding in the creek with three common redshank for comparison, noticeably "
            "longer billed and greyer. Left at half nine when the tide covered the mud and "
            "the roost dispersed. Full count submitted to the county recorder that evening.",
        ),
        (
            "garden bird list - running total",
            "Species recorded from the garden since we moved in, forty-three so far. Daily: "
            "blue tit, great tit, robin, blackbird, woodpigeon, dunnock, house sparrow, "
            "magpie. Regular on the feeders: goldfinch in a flock of up to fourteen on the "
            "nyjer, greenfinch less often than they used to be, coal tit which takes a seed "
            "and caches it, and a great spotted woodpecker on the fat block most mornings in "
            "winter. Occasional: sparrowhawk through the garden at speed, blackcap in "
            "February, siskin twice. Flyovers count: herring gull, cormorant, and a red kite "
            "drifting over in May. Nesting confirmed for blue tit in the box and blackbird in "
            "the hedge. New for the year would be a jay or a nuthatch.",
        ),
        (
            "Autumn migration notes - the headland",
            "Three mornings on the headland with an east wind and overnight rain, which is "
            "exactly the combination you want. Visible migration from first light: meadow "
            "pipits streaming through in ones and twos, several hundred over three hours, "
            "with chaffinch and a few siskin going over calling. In the bushes, redstart on "
            "the first morning, four willow warbler and a single pied flycatcher on the "
            "second, and on the third a yellow-browed warbler calling from the sycamores "
            "that took an hour to see properly. Wheatear on the short turf every day. "
            "Offshore, gannets feeding and a steady trickle of kittiwake. The wind swung "
            "south-west overnight and by the fourth morning the bushes were empty.",
        ),
        (
            "life list additions 2024",
            "Eleven new species this year. The yellow-browed warbler on the headland in "
            "October, seen properly in the end. Spotted redshank at the estuary in April, "
            "although I had heard one before without seeing it. Two from the trip north: "
            "black-throated diver on the loch in summer plumage and a pair of slavonian "
            "grebe. Ring ouzel on the moor in spring, a male on a drystone wall. Little gull "
            "over the reservoir after gales. Bearded tit at the reedbed reserve, heard "
            "pinging for twenty minutes before two flew across the channel. The rest are "
            "seabirds from the pelagic: storm petrel, sooty shearwater and a distant great "
            "shearwater that I am counting because three other people on the boat saw it "
            "better than I did.",
        ),
        (
            "reedbed_reserve_visit_notes",
            "Arrived before the reserve opened and walked the outer path to the far hide. "
            "Bittern boomed four times from the reedbed between seven and eight, which is "
            "the earliest I have heard one here. Marsh harrier quartering the reeds "
            "throughout, a female and a younger bird. Bearded tit pinging in the channel "
            "edge and eventually two crossed in front of the hide. On the open water: "
            "gadwall, shoveler, a dozen teal and three pochard. Cetti's warbler shouting from "
            "the scrub in at least four places along the path. Water rail squealing "
            "unseen. Left at eleven as it warmed up and the hirundines came through over the "
            "water, mostly sand martin with a few swallow among them.",
        ),
        (
            "kit notes - scope and binoculars",
            "The eight by forty-two binoculars remain the right choice for the garden and "
            "the woods, bright enough at dusk and light enough to carry all morning. The "
            "scope is essential on the estuary and the headland: at anything over two hundred "
            "metres the waders are unidentifiable without it, and picking a grey plover out "
            "of a dunlin flock needs the magnification. Tripod is too heavy and I leave it "
            "behind more often than I should, which is why half the distant seabirds go "
            "unrecorded. Clean the eyepieces properly after any morning with salt spray. "
            "Notebook in a plastic bag because pencil works in rain and ink does not. Always "
            "carry the county recorder's card so counts get submitted the same day.",
        ),
    ],
}

EXTENSIONS: dict[str, tuple[str, ...]] = {
    "baking_recipes": ("txt", "md", "docx", "pdf"),
    "novel_manuscript": ("docx", "odt", "txt", "epub"),
    "travel_itineraries": ("pdf", "docx", "txt"),
    "guitar_tabs_and_lyrics": ("txt", "md", "pdf"),
    "garden_planting_notes": ("txt", "md", "csv"),
    "house_renovation": ("docx", "pdf", "csv", "txt"),
    "fitness_training_log": ("csv", "txt", "md"),
    "book_club_notes": ("md", "docx", "txt", "rtf"),
    "wedding_planning": ("docx", "pdf", "csv", "odt"),
    "car_maintenance": ("txt", "pdf", "csv"),
    "language_learning_notes": ("md", "txt", "docx", "rtf"),
    "birdwatching_journal": ("txt", "md", "csv", "odt"),
}
