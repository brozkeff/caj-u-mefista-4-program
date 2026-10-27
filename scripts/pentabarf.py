"""Create Giggity-compatible Pentabarf XML from canonical data/program.json.

No website scraping happens at build time. Edit the JSON and run `make build`.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

from generate import ROOT, Lecture, parse_reviewed
from schedule_site import build_site


def duration_minutes(event: dict, same_day: list[dict]) -> int:
    """Return schedule-slot length, explicitly overridden when supplied.

    Args:
        event: Published programme event, possibly with duration_minutes.
        same_day: Time-ordered events on the same calendar day.

    Returns:
        Duration in minutes; inferred from the next start, capped by event type.
    """
    if 'duration_minutes' in event:
        return int(event['duration_minutes'])
    defaults={'lecture':45,'panel':60,'performance':30,'ceremony':30,'break':45,'activity':45,'social':60}
    limit=defaults.get(event['kind'],45)
    current=datetime.fromisoformat(event['date']+'T'+event['start'])
    after=[datetime.fromisoformat(x['date']+'T'+x['start']) for x in same_day if x['start'] and x['start']>event['start']]
    return max(5,min(limit,int((min(after)-current).total_seconds()/60))) if after else limit


def create(program:dict, lectures:list[Lecture], lang:str)->bytes:
    """Serialize published schedule as traditional Pentabarf XML.

    Args:
        program: Canonical conference data, including all timed programme events.
        lectures: Reviewed worksheet texts for lecture details.
        lang: `cz` or `en`.

    Returns:
        UTF-8 XML document with conference, day, room, event, persons and abstract.
    """
    lecture_by_id={l.event['id']:l for l in lectures}
    root=ET.Element('schedule')
    conference=ET.SubElement(root,'conference')
    meta={'title':'Čaj u Mefista 4' if lang=='cz' else "Tea at Mephisto’s 4",'subtitle':'Mezinárodní konference o výzkumu okultismu' if lang=='cz' else 'International Conference on Research into Occultism','venue':'Mahenův památník','city':'Brno','start':'2026-10-29','end':'2026-11-01','days':'4','day_change':'06:00:00','timeslot_duration':'00:05:00'}
    for k,v in meta.items(): ET.SubElement(conference,k).text=v
    days=defaultdict(list)
    for e in program['events']:
        if e['start']: days[e['date']].append(e)
    for i,day in enumerate(sorted(days),1):
        day_element=ET.SubElement(root,'day',{'index':str(i),'date':day})
        for room_name in sorted(set(e['room'] for e in days[day])):
            room=ET.SubElement(day_element,'room',{'name':room_name})
            for e in sorted([item for item in days[day] if item['room']==room_name],key=lambda o:o['start']):
                event=ET.SubElement(room,'event',{'id':str(1000+program['events'].index(e)),'guid':f"caj-u-mefista-4-{e['id']}"})
                elements={'start':e['start'],'duration':f"{duration_minutes(e,days[day])//60:02d}:{duration_minutes(e,days[day])%60:02d}",'room':room_name,'slug':e['id'],'title':e[f'title_{lang}'],'subtitle':'','track':e['kind'].capitalize(),'type':e['kind'],'language':', '.join(e.get('spoken_languages', [])) or 'und'}
                if e['id'] in lecture_by_id:
                    lecture=lecture_by_id[e['id']]
                    elements['abstract']=lecture.abstract_cz if lang=='cz' else lecture.abstract_en
                else:
                    elements['abstract']=e.get('notes','')
                elements['description']=''
                for k,v in elements.items(): ET.SubElement(event,k).text=v
                links=ET.SubElement(event,'links')
                ET.SubElement(links,'link',{'href':program['urls'][lang]}) .text = 'Live programme'
                people=ET.SubElement(event,'persons')
                for j,person in enumerate(e['persons'],1): ET.SubElement(people,'person',{'id':str(100000+program['events'].index(e)*10+j)}).text=person
                if e.get('moderator'):ET.SubElement(people,'person',{'id':str(100000+program['events'].index(e)*10+9)}).text=e['moderator']
    serialized=minidom.parseString(ET.tostring(root,encoding='utf-8')).toprettyxml(indent='  ',encoding='utf-8')
    return serialized


def main()->None:
    """CLI XML-only regeneration for urgent programme edits."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xlsx',type=Path,default=ROOT/'data'/'abstracts_review.xlsx')
    args=parser.parse_args()
    data=json.loads((ROOT/'data'/'program.json').read_text(encoding='utf-8'))
    lectures=parse_reviewed(args.xlsx,data)
    (ROOT/'schedule').mkdir(exist_ok=True)
    for lang in ('cz','en'):
        path=ROOT/'schedule'/f'Caj_u_Mefista_4_pentabarf_{lang}.xml'
        path.write_bytes(create(data,lectures,lang))
        print(f'{path}: {len(data["events"])} source events')
    build_site()


if __name__=='__main__':main()
