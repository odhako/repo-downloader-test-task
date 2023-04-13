import asyncio
from asyncio import Queue
import urllib.parse
import aiohttp
import aiofiles
import os
from tqdm import tqdm

repo_url = 'https://gitea.radium.group/radium/project-configuration'
parsed_url = urllib.parse.urlparse(repo_url)
# print(parsed_url)
api_url = '{0}://{1}/api/v1/repos{2}/contents'.format(parsed_url.scheme,
                                                      parsed_url.netloc,
                                                      parsed_url.path)


# https://gitea.radium.group/api/v1/repos/radium/project-configuration/contents


async def get_contents(session, url, files):
    async with session.get(url) as response:
        contents = await response.json()
        for item in contents:
            if item['type'] == 'dir':
                await get_contents(session, f'{url}/{item["path"]}', files)
            else:
                files.append(item)
    return files


async def worker(queue, session):
    while True:
        file = await queue.get()
        print(f'Working on {file["name"]}')
        async with session.get(file['download_url']) as response:
            text = await response.text()
            file_path = 'temp/' + file['path']
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            async with aiofiles.open(file_path, mode='w') as f:
                await f.write(text)
        print(f'Finished {file["name"]}')
        queue.task_done()


async def main():
    queue = Queue()

    async with aiohttp.ClientSession() as session:
        files = await get_contents(session, api_url, files=[])
        for file in files:
            await queue.put(file)

        tasks = []
        for i in range(3):
            task = asyncio.create_task(worker(queue, session))
            tasks.append(task)

        await queue.join()

        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


asyncio.run(main())
