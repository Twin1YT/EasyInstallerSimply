#!/usr/bin/env python
# coding: utf-8
def zipinstaller():
    import os
    import requests
    import gdown
    import requests

    linksraw = requests.get("https://raw.githubusercontent.com/Twin1YT/EasyInstallerSimply/main/OlderSeasons.txt")

    txt = linksraw.text

    lines = [line for line in txt.splitlines() if line.startswith('|')]

    lines = '\n'.join(lines)

    lines = '\n'.join(['{} {}'.format(i, line) for i, line in enumerate(lines.splitlines())])
    print(lines)

    links = [line for line in txt.splitlines() if line.startswith("https")]

    links = '\n'.join(links)

    linksnum = '\n'.join(['{} {}'.format(i, line) for i, line in enumerate(links.splitlines())])




    print("Select a build by typing the number next to it! ")
    build = input("Build: ")

    link = linksnum.splitlines()[int(build)]

    link = link.split()[1]
    r = requests.get(link)

    legit = r.url
    legit = legit.split('/')[-2]

    print("Where would you like to download the build to? ")
    path = input("Path: ")

    if not os.path.exists(path):
        print("The path you entered does not exist! ")
    else: 
        print("path found!")
    url = 'https://drive.google.com/uc?id=' + legit
    output = path
    gdown.download(url, output, quiet=False)
    print("Download complete!")
    with zipfile.ZipFile(output, 'r') as zip_ref:
        zip_ref.extractall(path)

import argparse
import csv
from ensurepip import version
import json
import logging
import os
import shlex
import subprocess
import time
import zipfile
import requests
import webbrowser
import tqdm

from distutils.util import strtobool
from getpass import getuser
from logging.handlers import QueueListener
from multiprocessing import freeze_support, Queue as MPQueue
from sys import exit, stdout, platform

from legendary import __version__, __codename__
from legendary.core import LegendaryCore
from legendary.models.exceptions import InvalidCredentialsError
from legendary.models.game import SaveGameStatus, VerifyResult
from legendary.utils.cli import get_boolean_choice, sdl_prompt
from legendary.utils.custom_parser import AliasedSubParsersAction
from legendary.utils.lfs import validate_files
from legendary.utils.selective_dl import get_sdl_appname
os.system('cls')
print("Which seasons do you want to download?")
print("[1] Season 1-7")
print("[2] Season 8-Latest")

choice = int(input(">> "))
if choice == 1:
    zipinstaller()
elif choice == 2:
    # todo custom formatter for cli logger (clean info, highlighted error/warning)
    logging.basicConfig(
        format='[%(name)s] %(levelname)s: %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger('cli')


    class LegendaryCLI:
        def __init__(self):
            self.core = LegendaryCore()
            self.logger = logging.getLogger('cli')
            self.logging_queue = None

        def setup_threaded_logging(self):
            self.logging_queue = MPQueue(-1)
            shandler = logging.StreamHandler()
            sformatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
            shandler.setFormatter(sformatter)
            ql = QueueListener(self.logging_queue, shandler)
            ql.start()
            return ql

        def install_game(self, manifest: str, game_folder: str, override_base_url: str):
            game = self.core.get_game('Fortnite', update_meta=True)
            base_game = None
            
            logger.info('Preparing download...')
            # todo use status queue to print progress from CLI
            # This has become a little ridiculous hasn't it?
            dlm, analysis, igame = self.core.prepare_download(game=game, base_game=base_game, base_path=None,force=None, max_shm=None,max_workers=None, game_folder=game_folder,disable_patching=None,override_manifest=manifest,override_old_manifest=None,override_base_url=override_base_url,platform_override=None,file_prefix_filter=None,file_exclude_filter=None,file_install_tag=None,dl_optimizations=None,dl_timeout=None,repair=None,repair_use_latest=None,disable_delta=None,override_delta_manifest=None)

            # game is either up to date or hasn't changed, so we have nothing to doc
            if not analysis.dl_size:
                logger.info('Download size is 0, the game is either already up to date or has not changed. Exiting...')
                if args.repair_mode and os.path.exists(repair_file):
                    igame = self.core.get_installed_game(game.app_name)
                    if igame.needs_verification:
                        igame.needs_verification = False
                        self.core.install_game(igame)

                    logger.debug('Removing repair file.')
                    os.remove(repair_file)
                exit(0)

            logger.info(f'Install size: {analysis.install_size / 1024 / 1024:.02f} MiB')
            compression = (1 - (analysis.dl_size / analysis.uncompressed_dl_size)) * 100
            logger.info(f'Download size: {analysis.dl_size / 1024 / 1024:.02f} MiB '
                        f'(Compression savings: {compression:.01f}%)')
            logger.info(f'Reusable size: {analysis.reuse_size / 1024 / 1024:.02f} MiB (chunks) / '
                        f'{analysis.unchanged / 1024 / 1024:.02f} MiB (unchanged / skipped)')
                        
            res = self.core.check_installation_conditions(analysis=analysis, install=igame, game=game,updating=False,ignore_space_req=None)

            if res.warnings or res.failures:
                logger.info('Installation requirements check returned the following results:')

            if res.warnings:
                for warn in sorted(res.warnings):
                    logger.warning(warn)

            if res.failures:
                for msg in sorted(res.failures):
                    logger.fatal(msg)
                logger.error('Installation cannot proceed, exiting.')
                if not input('Do you want to continue anyway (y/N): ').lower().startswith('y'):
                    exit(1)

            logger.info('Downloads are resumable, you can interrupt the download with '
                        'CTRL-C and resume it using the same command later on.')

            start_t = time.time()

            try:
                # set up logging stuff (should be moved somewhere else later)
                dlm.logging_queue = self.logging_queue
                dlm.proc_debug = None

                dlm.start()
                dlm.join()
            except Exception as e:
                end_t = time.time()
                logger.info(f'Installation failed after {end_t - start_t:.02f} seconds.')
                logger.warning(f'The following exception occured while waiting for the donlowader to finish: {e!r}. '
                            f'Try restarting the process, the resume file will be used to start where it failed. '
                            f'If it continues to fail please open an issue on GitHub.')
            else:
                end_t = time.time()
                logger.info(f'Finished installation process in {end_t - start_t:.02f} seconds.')

    def main():
        versions = requests.get('https://raw.githubusercontent.com/Twin1YT/EasyInstallerSimply/main/Manifests.json').json()
        versions_s = sorted(versions.keys(), key=lambda x: float(str(x.split('-')[1].split('-')[0]).replace('.x', '').replace('Cert', '0')))
        versions_links = versions.values()

        if platform.startswith('win32'):
            installations = os.getenv('APPDATA')
        else:
            installations = './'
            
        if not os.path.isdir(installations + '/EasyInstaller'):
            os.mkdir(installations + '/EasyInstaller')
            
        installations = installations + '/EasyInstaller/installations.json'
        
        if not os.path.isfile(installations):
            json.dump([], open(installations, 'w'))
        
        file = json.load(open(installations))

        print('\nAvailable manifests:')
        for idx, build_version_string in enumerate(versions_s):
            print(f' * [{idx}] {build_version_string}')
        print(f'\nTotal: {len(versions)}')
        if len(file) > 0:
            print(f'Type C, if you want to continue any of {len(file)} download(s)')
        print("Type D, if you want to use a custom manifest")
            
        cli = LegendaryCLI()
        
        idx = input('Please enter the number before the Build Version to select it: ') 

        if idx.lower().startswith('c') and len(file) > 0:
            for x, y in enumerate(file):
                print(f' * [{x}] {y["name"]} | {y["game_folder"]}')
            idx = int(input('Please enter a number of the version you want to continue downloading: '))
            cli.install_game(file[idx]["version"], file[idx]["game_folder"], file[idx]["override_base_url"])
        if idx.lower().startswith('d'):
            manifest_url = input('Please input a custom manifest directory/url: ')
            game_folder = input('Please enter a game folder location: ')
            
            path_block = [ '*', '?', '"', '<', '>', '|' ]

            for x in path_block: 
                game_folder = game_folder.replace(x, '')

            with open(installations, "w") as write_file:
                file.append({
                    "name": manifest_url,
                    "version": manifest_url,
                    "override_base_url": "https://epicgames-download1.akamaized.net/Builds/Fortnite/CloudDir",
                    "game_folder": game_folder
                })
                json.dump(file, write_file)
            # Yep, no android manifest support
            cli.install_game(manifest_url, game_folder, "https://epicgames-download1.akamaized.net/Builds/Fortnite/CloudDir")
            cli.core.exit()
        else:
            idx = int(idx)
            game_folder = input('Please enter a game folder location: ')

            path_block = [ '*', '?', '"', '<', '>', '|' ]

            for x in path_block:
                game_folder = game_folder.replace(x, '')
            
        
            if '-Windows' in versions_s[idx]:
                override_base_url = 'https://epicgames-download1.akamaized.net/Builds/Fortnite/CloudDir'
            else:
                override_base_url = 'https://epicgames-download1.akamaized.net/Builds/Fortnite/Content/CloudDir'
            
            if '&confirm=t' in versions_links[idx]:
                
                with open("Fortnite.zip", "wb").write(requests.get(versions_s[idx]).content):
                    
                    with tqdm(total=100) as pbar:
                        with zipfile.ZipFile("Fortnite.zip", "r") as zip_ref:
                            zip_ref.extractall()
                        os.remove("Fortnite.zip")
                    pbar.update(100)

            else:
                with open(installations, "w") as write_file:
                    file.append({
                        "name": versions_s[idx],
                        "version": versions[versions_s[idx]],
                        "override_base_url": override_base_url,
                        "game_folder": game_folder
                    })
                    json.dump(file, write_file)
                cli.install_game(versions[versions_s[idx]], game_folder, override_base_url)
        cli.core.exit()
        print("Credits:")
        print("Derrod for creating legendary")
        print("Lupus for originally creating EasyInstaller")
        print("Kyiro for maintaining EasyInstaller")
        print("Download finished!")
        print("You can close this window now")
        input('')

    if __name__ == '__main__':
        # required for pyinstaller on Windows, does nothing on other platforms.
        freeze_support()
        main()
else: 
    print("Not a valid choice!")
    os.system('start_download.bat')
    
