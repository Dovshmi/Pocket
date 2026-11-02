"""Local, bounded Quick Search for Pocket; no network or automatic execution."""
from __future__ import annotations
from . import command_helper as ch
from . import compact_dashboard as compact

def results(data, commands, query, enabled, *, limit=18):
    if not isinstance(query, str) or not query.strip():
        return []
    allowed=set(enabled)
    found=[]
    normalized=ch.normalize(query)
    for key, icon, label in compact.NAVIGATION:
        if key=="home" or (key!="settings" and key not in allowed):
            continue
        if normalized in ch.normalize(label+" "+compact.PAGES[key][1]):
            found.append({"kind":"tool","destination":key,"id":key,"title":label,"subtitle":"Open tool"})
    if "notes" in allowed:
        for n in data.get("notes",[]):
            if not isinstance(n,dict): continue
            title=n.get("title","")
            body=n.get("body","")
            if isinstance(title,str) and isinstance(body,str) and (normalized in ch.normalize(title) or normalized in ch.normalize(body)):
                found.append({"kind":"note","destination":"notes","id":n.get("id"),"title":title or "Untitled note","subtitle":"Note"})
                if len(found)>=limit*2: break
    if "links" in allowed:
        for entry in data.get("links",[]):
            if not isinstance(entry,dict): continue
            title=entry.get("title","")
            target=entry.get("url","")
            if isinstance(title,str) and isinstance(target,str) and (normalized in ch.normalize(title) or normalized in ch.normalize(target)):
                found.append({"kind":"shortcut","destination":"links","id":entry.get("id"),"title":title or "Shortcut","subtitle":"Saved shortcut"})
                if len(found)>=limit*3: break
    if "commands" in allowed:
        for cmd in ch.find_commands(commands,query=query)[:limit]:
            found.append({"kind":"command","destination":"commands","id":cmd["id"],
                          "title":cmd["description"] or cmd["machine"],
                          "subtitle":cmd["machine"]+" · CLI","query":query})
    return found[:max(1,limit)]
