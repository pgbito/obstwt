
import argparse
import asyncio
import os, sys
from json import dump, loads ,decoder, dumps
import aiohttp


default = 'python obsinsta.py [-h] [-o OUTPUT_DIR] -u USERNAME -s SESSIONID'
loguito = f"""
                        {default}
                        
Para utilizar este script, necesitas proporcionar tu ID de sesión de Instagram. El ID de sesión es tu sesión de inicio de sesión de Instagram,
 y es necesario para autenticar tus solicitudes a la API de Instagram.

Para obtener tu ID de sesión de Instagram, puedes seguir estos pasos:

    Abre Instagram en tu navegador web.
    Inicia sesión en tu cuenta de Instagram.
    Haz clic con el botón derecho en la página y selecciona "Inspeccionar" para abrir las herramientas para desarrolladores del navegador.
    En las herramientas para desarrolladores, ve a la pestaña "Aplicación".
    En la barra lateral izquierda, despliega la sección "Cookies" y selecciona "https://www.instagram.com".
    Busca una cookie llamada "sessionid" y copia su valor.

 ▄▀▀▀▀▄   ▄▀▀█▄▄   ▄▀▀▀▀▄  ▄▀▀▀█▀▀▄  ▄▀▀▄    ▄▀▀▄  ▄▀▀▀█▀▀▄      ▄▀▀▀█▀▀▄  ▄▀▀▀▀▄   ▄▀▀▀▀▄   ▄▀▀▀▀▄     
█      █ ▐ ▄▀   █ █ █   ▐ █    █  ▐ █   █    ▐  █ █    █  ▐     █    █  ▐ █      █ █      █ █    █      
█      █   █▄▄▄▀     ▀▄   ▐   █     ▐  █        █ ▐   █         ▐   █     █      █ █      █ ▐    █      
▀▄    ▄▀   █   █  ▀▄   █     █        █   ▄    █     █             █      ▀▄    ▄▀ ▀▄    ▄▀     █       
  ▀▀▀▀    ▄▀▄▄▄▀   █▀▀▀    ▄▀          ▀▄▀ ▀▄ ▄▀   ▄▀            ▄▀         ▀▀▀▀     ▀▀▀▀     ▄▀▄▄▄▄▄▄▀ 
         █    ▐    ▐      █                  ▀    █             █                             █         
         ▐                ▐                       ▐             ▐                             ▐         
                                                                                                         by pgbito"""

PROJECT_DIR = os.path.split(__file__)[0]
handlers ={'json': aiohttp.ClientResponse.json, 'raw': aiohttp.ClientResponse.read, 'plain' :aiohttp.ClientResponse.text ,"instance" :None}
async def fetch(url, session :aiohttp.ClientSession, headers=None, cookies=None, params=None, handler='json' )-> dict |aiohttp.ClientResponse |list |bytes |str:
    async with session.get(url, headers=headers, cookies=cookies, params=params) as response:

        hdlr = handlers.get(handler)
        if not hdlr :
            return response
        return await hdlr(response)


async def ig_request(hash_id, variables, resolver, client, cookies=None, sleep_error=5,
                     reintentos=3):
    has_next_page = True
    reintentos_actuales = 0

    params = {
        "query_hash": hash_id,
        "variables": dumps(variables)
    }

    while has_next_page and reintentos_actuales < reintentos:

        resp = await fetch("https://www.instagram.com/graphql/query/", params=params, cookies=cookies ,session=client
                           ,handler='json')


        if True:
            reintentos_actuales = 0

            try:
                has_next_page = resolver(variables, resp)

                if has_next_page:
                    params["variables"] = dumps(variables)

            except Exception as err:
                print("Se prudujo un error en el resolver:", err)

                reintentos_actuales += 1

                print(
                    "Se ha producido un error en la petición, estamos realizando el reintento %d de %d reintentos posibles." % (
                        reintentos_actuales, reintentos))

                await asyncio.sleep(sleep_error)

    return reintentos_actuales < reintentos








followers = set()
followings = set()


def resolver_following(variables, data_resp):


    data_resp = data_resp["data"]["user"]["edge_follow"]

    # iteramos sobre los usuarios que obtuvimos


    followings.update(map(lambda node: node["node"]["username"], data_resp["edges"]))

    if data_resp["page_info"]["has_next_page"]:
        variables["after"] = data_resp["page_info"]["end_cursor"]
        return True

    return False

def resolver_followers(variables, data_resp):
    data_resp = data_resp["data"]["user"]["edge_followed_by"]



    followers.update(map(lambda node: node["node"]["username"], data_resp["edges"]))

    if data_resp["page_info"]["has_next_page"]:
        variables["after"] = data_resp["page_info"]["end_cursor"]
        return True

    return False
def create_parser():
    parser = argparse.ArgumentParser(usage=loguito,add_help=True)

    parser.add_argument("-u", '--username',required=True ,type=str)
    parser.add_argument("-s" ,"--sessid" ,required=True ,type=str)

    parser.add_argument("-o", "--output_dir", default=os.path.abspath("./output"))

    return parser.parse_args()
async def getUserId(username, sessionsId ,session):
    cookies = {'sessionid': sessionsId}
    headers = {'User-Agent': 'Instagram 64.0.0.14.96'}
    api = await session.get(
        f'https://www.instagram.com/{username}/?__a=1&__d=dis',
        headers=headers,
        cookies=cookies
    )
    try:
        if api.status == 404:
            return {"id": None, "error": "User not found"}
        data = await api.json()
        id = data["logging_page_id"].strip("profilePage_")
        return {"id": id, "error": None, **data}

    except decoder.JSONDecodeError:
        return {"id": None, "error": "Rate limit"}
async def get_followers_list(id, cookies, client):
    variables = {
        "id": id,
        "first": 50
    }

    return await  ig_request("c76146de99bb02f6415203be841dd25a", variables, resolver_followers, client, cookies=cookies)

async def get_following_list(id, cookies ,client):
    variables = {
        "id": id,
        "first": 50
    }

    success = await ig_request("d04b0a864b4b54837c0d870b0e77e076", variables, resolver_following, client,
                               cookies=cookies)
    return success


async def main(args):
    args.output_dir = os.path.join(
        os.path.abspath(args.output_dir), args.username)
    os.makedirs(args.output_dir, exist_ok=True)

    cookies = {
        "sessionid" :args.sessid
    }
    async with aiohttp.ClientSession() as client:
        try:
            infos: dict = await getUserId(args.username, cookies["sessionid"] ,client)
            if infos["error"]:
                raise KeyError(infos["error"])
            args.userid =infos["id"]
            print("ID obtenida:", args.userid)
        except KeyError as e:
            print('El usuario solicitado no existe o te ha bloqueado, o tu sessionid ha expirado', e)
            sys.exit(-1)

        followersuccess = await get_followers_list(args.userid, cookies, client)
        if not followersuccess:
            print("Se ha producido un error al obtener la lista de seguidores de %s." % (args.username))
        else:
            with open(os.path.join(args.output_dir,
                                   "{username}_followers.json".format(username=args.username)),
                      "w") as f:
                dump(tuple(followers), f)
            print("Se guardaron todos los usuarios de {} seguidos de {}".format(len(followers),
                                                                                                   args.username))

        print("\n" + "-" * 50 + "\n")
        followingsuccess = await get_following_list(args.userid, cookies, client)
        if not followingsuccess:
            print("Se ha producido un error al obtener la lista de seguidos por %s." % (args.username))
        else:
            with open(os.path.join(args.output_dir,
                                   "{username}_followings.plain.json".format(username=args.username)),
                      "w") as f:

                dump(tuple(followings), f)

    with open(os.path.join(args.output_dir, "{username}_mutual.json".format(username=args.username)),
              "w") as f:
        mutual = followers & followings
        dump(tuple(mutual), f)
    with open(os.path.join(args.output_dir, "{username}_nomutual.json".format(username=args.username)),
              "w") as f:

        dump(tuple(followings ^ mutual), f)

    print("Se guardaron todos los usuarios de {} seguidos de {}".format(
        len(followings), args.username))
    os.startfile(args.output_dir)

    return cookies



if __name__ == '__main__':
    cwd = __file__.split(os.path.sep)
    cwd.pop()
    cwd = os.path.sep.join(cwd)
    os.chdir(cwd)

    args = create_parser()
    os.system('cls' if os.name == 'nt' else 'clear')
    print(loguito.replace(default, " ".join(sys.orig_argv)))
    asyncio.run(main(args))
