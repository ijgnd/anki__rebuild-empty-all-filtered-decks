# Add-on for Anki
#
# License: AGPLv3 (license of the original release, see
#     https://web.archive.org/web/20200225134227/https://ankiweb.net/shared/info/1639597619
#
# This is a modification of Arthur's modification khonkhortisan's
# port of Arthaey "Rebuild All & Empty All" which was originally released at
# https://ankiweb.net/shared/info/1639597619
#
# Contributors:
# - Arthaey Angosii, https://github.com/Arthaey
# - ankitest
# - ArthurMilchior
# - ijgnd


import threading
from anki.cards import Card
import time
from anki.lang import _
from anki.hooks import wrap
from aqt import mw
from aqt.deckbrowser import DeckBrowser
from aqt.utils import tooltip


def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    return fail


def _updateFilteredDecks(actionFuncName):
    dynDeckIds = [ d["id"] for d in mw.col.decks.all() if d["dyn"] ]
    count = len(dynDeckIds)

    if not count:
        tooltip("No filtered decks found.")
        return

    # should be one of "rebuildDyn" or "emptyDyn"
    actionFunc = getattr(mw.col.sched, actionFuncName)

    mw.checkpoint("{0} {1} filtered decks".format(actionFuncName, count))
    mw.progress.start()
    [ actionFunc(did) for did in sorted(dynDeckIds) ]
    mw.progress.finish()
    tooltip("Updated {0} filtered decks.".format(count))

    mw.reset()


def _handleFilteredDeckButtons(self, url):
    if url in ["rebuildDyn", "emptyDyn"]:
        _updateFilteredDecks(url)


def _addButtons(self):
    drawLinks = [
        ["", "rebuildDyn", _("Rebuild All")],
        ["", "emptyDyn", _("Empty All")]
    ]
    # don't duplicate buttons every click
    if drawLinks[0] not in self.drawLinks:
        self.drawLinks += drawLinks

DeckBrowser._drawButtons = wrap(DeckBrowser._drawButtons, _addButtons, "before")
DeckBrowser._linkHandler = wrap(DeckBrowser._linkHandler, _handleFilteredDeckButtons, "after")


lastReview = None
def postSched(self):
    global lastReview
    delta = gc("auto rebuild interval")
    print("maybe auto rebuild filtered decks")
    if delta and (lastReview is None or time.time() > lastReview + delta):
        print("....doing it")
        _updateFilteredDecks("rebuildDyn")
        lastReview = time.time()
Card.flushSched = wrap(Card.flushSched, postSched)
Card.sched = wrap(Card.flush, postSched)
