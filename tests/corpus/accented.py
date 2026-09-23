"""English documents thick with accented words.

Ordinary English writing is full of them — loanwords, composers' names, place
names, culinary terms — and an ASCII tokeniser quietly destroys the word around
each one: ``Déclaration`` became ``claration``, ``café`` became ``caf``. These
two subjects exist to keep that fixed, so both filenames and bodies carry
diacritics heavily.

The subjects are deliberately chosen to sit far from the other thirty-five, so
that adding them sharpens the corpus rather than blurring it.
"""

from __future__ import annotations

TOPICS: dict[str, list[tuple[str, str]]] = {
    "orchestral_programme": [
        (
            "Spring programme - Fauré and Dvořák",
            "The spring programme opens with Fauré's Pavane before the orchestra "
            "turns to Dvořák. The répétiteur has asked for an extra sectional on "
            "the slow movement, where the strings drift behind the woodwind. "
            "Saint-Saëns fills the second half, and the conductor wants the tempo "
            "rubato kept restrained throughout. Programme notes are due to the "
            "printer on the fifteenth, so the orchestra manager needs the final "
            "running order this week.",
        ),
        (
            "répétiteur notes - string sectional",
            "Notes from the string sectional. The orchestra still rushes the "
            "Dvořák scherzo, and the répétiteur marked the passage where the "
            "cellos anticipate the conductor. Fauré's writing for divided violas "
            "needs a warmer tone than the section is giving it. We rehearse the "
            "Saint-Saëns finale next, and the leader asked for bowings to be "
            "agreed before the tutti rehearsal so the orchestra is not sorting "
            "them out on the night.",
        ),
        (
            "Concert programme notes draft - Saint-Saëns",
            "Draft programme notes for the Saint-Saëns. The composer wrote the "
            "work for a provincial orchestra and it shows in the modest woodwind "
            "writing. Our conductor prefers a brisk tempo, closer to Fauré's own "
            "markings than to the tradition of rubato that later orchestras "
            "adopted. The programme pairs it with Dvořák, whose scoring for brass "
            "is far heavier, so the balance in rehearsal will need attention.",
        ),
        (
            "orchestra rehearsal schedule - Dvořák week",
            "Rehearsal schedule for Dvořák week. Monday is a full orchestra call, "
            "Tuesday a woodwind sectional with the répétiteur, and Wednesday the "
            "conductor takes the strings alone. The Fauré is on the stands from "
            "Thursday. Players are reminded that the concert programme runs "
            "without an interval, so the Saint-Saëns follows straight on and the "
            "orchestra should not leave the platform between works.",
        ),
        (
            "Fauré - tempo and rubato discussion",
            "A long discussion with the conductor about rubato in the Fauré. He "
            "argues that the orchestra should keep the pulse and let the soloist "
            "stretch above it, which is closer to how Saint-Saëns conducted his "
            "own music. The répétiteur disagrees and wants the whole orchestra "
            "breathing together. We will try both in rehearsal before the "
            "programme is finalised, and the Dvořák stays strictly in tempo.",
        ),
        (
            "orchestra committee - programme for the autumn",
            "The orchestra committee met to settle the autumn programme. Dvořák "
            "is confirmed, Fauré is likely, and the conductor has asked whether "
            "the players would welcome more Saint-Saëns. Several members felt the "
            "spring programme leaned too heavily on rubato-laden repertoire and "
            "asked for something brisker. The répétiteur will circulate parts "
            "once the orchestra manager confirms the hire library can supply "
            "them in time.",
        ),
    ],
    "patisserie_notes": [
        (
            "crème brûlée - third attempt",
            "Third attempt at the crème brûlée. The custard split again, so next "
            "time the crème goes into the oven at a lower temperature in a bain "
            "marie. The sugar on top caramelised unevenly under the blowtorch. "
            "Pâtisserie books all insist on straining the crème before it goes "
            "into the ramekins, and I keep skipping it. The soufflé recipe from "
            "the same book worked first time, so the fault is mine rather than "
            "the method.",
        ),
        (
            "pâte à choux notes",
            "Pâte à choux for éclairs. Dry the paste properly over the heat "
            "before the eggs go in, or the choux will not rise. The pâtisserie "
            "chef said to listen for the paste squeaking against the pan. Piped "
            "éclairs need an even thickness or they bake crooked. Crème "
            "pâtissière goes in once they are completely cold, and the fondant "
            "should be warmed only to blood temperature before glazing.",
        ),
        (
            "macaron troubleshooting - feet and shells",
            "Macaron shells cracked again and the feet spread sideways. The "
            "meringue was probably under-whipped, or the macaronage went too far. "
            "Let the piped shells form a skin before they go in the oven. The "
            "pâtisserie course notes say to rest them at least thirty minutes. "
            "Crème au beurre for the filling was far too sweet; next time use the "
            "crème pâtissière instead and cut the sugar.",
        ),
        (
            "soufflé au fromage - for Saturday",
            "Soufflé au fromage for Saturday. Butter the ramekins upwards so the "
            "soufflé climbs, and get the béchamel properly thick before folding "
            "the whites through. The pâtisserie principle is the same as for the "
            "sweet soufflés: fold gently, lose as little air as possible, and do "
            "not open the oven. Serve straight from the oven, because a soufflé "
            "waits for nobody.",
        ),
        (
            "crêpes and galettes - Sunday",
            "Crêpe batter rested overnight, which made a noticeable difference. "
            "The galettes need buckwheat flour and a much hotter pan than the "
            "sweet crêpes. Crème fraîche and a little sugar is enough for the "
            "sweet ones. The pâtisserie book suggests clarified butter for the "
            "pan, and it does stop them catching. Next time make the batter "
            "thinner still so the crêpes are properly lacy.",
        ),
        (
            "éclair glaçage and fillings",
            "Notes on glaçage for the éclairs. Fondant must be warmed gently or "
            "it loses its shine and sets dull. Dip rather than spread, and wipe "
            "the edge cleanly. Fillings so far: crème pâtissière with vanilla, "
            "crème with coffee, and a chocolate crème that was too stiff to pipe. "
            "The pâtisserie shop near the café does a salted caramel éclair worth "
            "copying once the choux is reliable.",
        ),
    ],
}

EXTENSIONS: dict[str, tuple[str, ...]] = {
    "orchestral_programme": ("docx", "pdf", "txt", "odt"),
    "patisserie_notes": ("txt", "md", "docx", "rtf"),
}
