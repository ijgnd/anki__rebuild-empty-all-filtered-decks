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


def rebuilt_nested_first(dynDeckIds, actionFunc):
    nestedlevels = {}
    for id in dynDeckIds:
        deck = mw.col.decks.get(id)
        n = deck['name'].count("::")
        nestedlevels.setdefault(n, []).append(str(id))
    for level in sorted(nestedlevels, key=nestedlevels.get, reverse=False):
        for e in nestedlevels[level]:
            actionFunc(e)


def _updateFilteredDecks(actionFuncName):
    dynDeckIds = sorted([d["id"] for d in mw.col.decks.all() if d["dyn"]])
    count = len(dynDeckIds)
    if not count:
        tooltip("No filtered decks found.")
        return
    # should be one of "rebuildDyn" or "emptyDyn"
    actionFunc = getattr(mw.col.sched, actionFuncName)
    mw.checkpoint("{0} {1} filtered decks".format(actionFuncName, count))
    mw.progress.start()
    if actionFuncName == "emptyDyn":
        # [actionFunc(did) for did in sorted(dynDeckIds)]
        for did in dynDeckIds:
            actionFunc(did)
    else:
        build_first = gc("build first")
        if build_first and isinstance(build_first, list):
            for dname in build_first:
                deck = mw.col.decks.byName(dname)
                if deck and deck.id in dynDeckIds:
                    actionFunc(deck.id)
                    dynDeckIds.remove(deck.id)
        build_last = gc("build last")
        if build_last and isinstance(build_last, list):
            for dname in build_last:
                deck = mw.col.decks.byName(dname)
                if deck and deck.id in dynDeckIds:
                    dynDeckIds.remove(deck.id)
                else:
                    build_last.remove(dname)
        if gc("build - prioritize most nested subdecks"):
            rebuilt_nested_first(dynDeckIds, actionFunc)    
        else:
            [actionFunc(did) for did in sorted(dynDeckIds)]
        if build_last:
            for dname in build_last:
                deck = mw.col.decks.byName(dname)
                actionFunc(deck['id'])
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
