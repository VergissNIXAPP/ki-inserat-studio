"""Validierung unabhängig von Hosting und Webframework."""
import json, math

def question_list(value):
    if value is None or value == '': return []
    values = value if isinstance(value,list) else [value]
    return [v.strip() if isinstance(v,str) else json.dumps(v,ensure_ascii=False)
            for v in values if v is not None and v != '']

def normalize_analysis(value):
    if not isinstance(value,dict): raise ValueError('KI-Antwort ist kein Objekt')
    result={}
    for key in ('title','description','category','brand','model','condition','pricing_note','search_terms'):
        item=value.get(key,'')
        if item is None:item=''
        if not isinstance(item,str): raise ValueError('Ungültiges Textfeld: '+key)
        result[key]=item.strip()
    if not result['title'] or not result['description']:raise ValueError('Titel oder Beschreibung fehlt')
    result['title']=result['title'][:65]
    result['description']=result['description'][:4000]
    result['questions']=question_list(value.get('questions'))
    price=value.get('price_eur')
    try:
        if isinstance(price,bool):raise ValueError()
        price=float(str(price).replace(',','.'))
        if not math.isfinite(price) or not 0<price<=99999999:raise ValueError()
        result['price_eur']=round(price,2)
    except (ValueError,TypeError):result['price_eur']=None
    return result

def is_access_block(text):
    text=text.lower()
    return any(x in text for x in ('ip-bereich vorübergehend gesperrt','ip-bereich gesperrt',
        'access denied','automated access','verify you are human','checking your browser'))
