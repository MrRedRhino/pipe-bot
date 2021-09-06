import json
from os import listdir

langs = listdir('lang')
translations = {}
for path in listdir('lang'):
    f = open(f'lang/{path}')
    translations[path] = (json.load(f))
    f.close()


def translate(key, lang, param0=None, param1=None, param2=None, param3=None, param4=None):
    global translations
    lang += '.json'

    if lang not in translations.keys():
        print(f'Error 404 - Languagefile {lang} not found')
        return key
    elif key not in translations[lang].keys():
        print(f'Error 404 - Key {key} not found in languagefile {lang}')
        return key
    else:
        return translations[lang][key].format(param0, param1, param2, param3, param4)
