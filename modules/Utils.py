import asyncio
import io
import json
import os
import urllib
from contextlib import redirect_stdout
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from discord_slash import SlashCommand, cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice, create_permission
from discord_slash.model import SlashCommandOptionType
import sys
import random
import configparser

sys.path.append('..')
from Lib import Logger, embed_generator, pluralize, perms

BTC_PRICE_URL_coinmarketcap = 'https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert=RUB'
config = configparser.ConfigParser()
config.read('setting.ini')
STREAMING_STATUS_TEXT = config.get('Setting', 'streaming_status_text')


class Utils(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    logger = Logger()

    @cog_ext.cog_slash(name='btc',
                       description='Реклама YOBA в описании SERVO-BOT',
                       options=[
                           create_option(name='money_code', description='Укажите желаюмую валюту',
                                         option_type=SlashCommandOptionType.STRING, required=True,
                                         choices=[
                                             create_choice('USD', 'Доллар'),
                                             create_choice('RUB', 'Рубли')
                                         ])
                       ])
    async def crypto(self, ctx: SlashContext, money_code: str = 'USD'):
        limit = 8
        API_KEY_COINMARKET = os.environ.get('API_KEY_COINMARKET')
        url_usd = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/' \
                  f'listings/latest?start=1&limit={limit}&convert={money_code}&CMC_PRO_API_KEY={API_KEY_COINMARKET}'
        req = requests.get(url_usd)
        req_json = req.json()
        embed = discord.Embed(title="Стоимости криптовалют",
                              description="Стоимость криптовалют на данный момент по данным биржи coinmarketcap.",
                              color=0xd5de21)
        for i in req_json['data']:
            price = str(i['quote'][money_code]['price'])
            embed.add_field(name=i['name'], value=price, inline=True)
            embed.add_field(name='Изменения за Сутки',
                            value="[{}]".format(
                                round(((int(float(price)) / 100) * int(float(i['quote'][money_code]
                                                                             ['percent_change_24h']))), 1)),
                            inline=True)
            embed.add_field(name='Неделю',
                            value="[{}]".format(
                                round(((int(float(price)) / 100) * int(float(i['quote'][money_code]
                                                                             ['percent_change_7d']))), 1)), inline=True)
        await ctx.send(embed=embed)
        self.logger.comm('crypto_price')

    @cog_ext.cog_slash(name='bash',
                       description='Выполнив команду, бот отправит в чат случайную цитату из bash.im')
    async def bash(self, ctx: SlashContext):
        from bs4 import BeautifulSoup
        url = 'https://bash.im/random'
        rs = requests.get(url)
        root = BeautifulSoup(rs.text, 'html.parser')
        mydivs = root.find("div", {"class": "quote__body"})
        quote = mydivs.getText('\n', strip=True)
        await ctx.send(embed=embed_generator('Рандомная цитата с Bash.im', str(quote)))
        self.logger.comm(f'BASH. Author: {ctx.author}')

    # -----------------------------------------Start of IteratorW Code -------------------------------------------------
    class MyGlobals(dict):
        def __init__(self, globs, locs):
            super().__init__()
            self.globals = globs
            self.locals = locs

        def __getitem__(self, name):
            try:
                return self.locals[name]
            except KeyError:
                return self.globals[name]

        def __setitem__(self, name, value):
            self.globals[name] = value

        def __delitem__(self, name):
            del self.globals[name]

    def _exec(self, code, g, l):
        out = io.StringIO()
        d = Utils.MyGlobals(g, l)
        try:
            error = False
            with redirect_stdout(out):
                exec(code, d)
        except Exception as ex:
            error = True
            out.write(str(ex))

        return out.getvalue(), error

    @staticmethod
    def _await(coro):  # це костыль для выполнения асинхронных функций в exec
        asyncio.ensure_future(coro)

    @cog_ext.cog_slash(name='exec',
                       description='Эта команда позволяет выполнять код.', permissions=perms,
                       options=[create_option(name='code', description='Код на Питухоне',
                                              option_type=SlashCommandOptionType.STRING, required=True)])
    async def execute(self, ctx: SlashContext, code: str):
        code = code.replace("```", "")
        out, is_error = self._exec(code.strip().rstrip(), globals(), locals())

        if is_error:
            await ctx.send(embed=embed_generator('⚠️ Криворукий уебан, у тебя ошибка! ⚠️', out))
            self.logger.error(f'Unsuccessful attempt to execute code. Author: {ctx.author}\n{out}')
        else:
            await ctx.send(embed=embed_generator('Код успешно выполнен!', out))
            self.logger.comm(f'EXECUTE. Author: {ctx.author}')

    #  --------------------------------------End of ITERATORW Code------------------------------------------------------
    @cog_ext.cog_slash(name='coub', description='Открывает коуб прямо в чате!')
    async def coub(self, ctx: SlashContext, url_to_coub: str):
        url = "http://coub.com//api/v2/coubs" + url_to_coub[21:]
        r = requests.get(url)
        coub_data = r.json()
        views = coub_data["views_count"]
        title = coub_data["title"]
        url_to_ass = "https://coubassistant.com/en/web"
        payload = f"-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"urlpost\"\r\n\r\n{url_to_coub}\r\n-----011000010111000001101001--\r\n"
        headers = {'content-type': 'multipart/form-data; boundary=---011000010111000001101001'}
        response = requests.request("POST", url_to_ass, data=payload, headers=headers)
        result = BeautifulSoup(response.text, 'html.parser')
        song = coub_data["file_versions"]["html5"]['audio']['high']
        song_name = result.findAll('h3')[0].getText()
        if song_name == 'Easy way to search for music':
            song_name = 'Музыка не найдена!'
        try:
            link = coub_data["file_versions"]["share"]["default"]
        except Exception as e:
            await result_embed('Упс...', 'Что-то пошло не так, проверьте ссылку', ctx)
            return
        await ctx.send(
            f'Название: ``{title}``\nПросмотров: ``{views}``\nМузыка из Куба: ``{song_name}``\nСсылка: {link} '
            f'\nАудио: {song["url"]}   {round(song["size"] / 1048576, 2)}mB')
        self.logger.comm(f'COUB. Author: {ctx.message.author}')

    @cog_ext.cog_slash(name='rainbow',
                       description='Реклама YOBA в говнокоде Python', permissions=perms,
                       options=[create_option(name='state', description='Статус радуги',
                                              option_type=SlashCommandOptionType.BOOLEAN,
                                              required=True)])
    async def change_rainbow(self, ctx: SlashContext, state: bool):
        rainbow_role_name = config.get('Setting', 'role_rainbow')
        rainbow_role_status = bool(config.get('Setting', 'role_rainbow_status'))
        role = discord.utils.get(ctx.guild.roles, name=rainbow_role_name)
        if role is not None:
            if state and not rainbow_role_status:
                config.set('Setting', 'role_rainbow_status', 'True')
                with open('setting.ini', 'w', encoding='utf-8') as configFile:
                    config.write(configFile)
                await ctx.send(embed=embed_generator('Модуль [RAINBOW]', 'Включен!'))
                self.logger.comm(f'[RAINBOW] Turn On! Guild: {ctx.guild.name}')
            elif not state and rainbow_role_status:
                config.set('Setting', 'role_rainbow_status', 'False')
                with open('setting.ini', 'w', encoding='utf-8') as configFile:
                    config.write(configFile)
                await ctx.send(embed=embed_generator('Модуль [RAINBOW]', 'Выключен!'))
                self.logger.comm(f'[RAINBOW] Turn Off! Guild: {ctx.guild.name}')
        else:
            try:
                await discord.Guild.create_role(ctx.guild,
                                                name='Rainbow',
                                                hoist=True,
                                                reason='SERVO-BOT Автоматическое добавление роли!')
                await ctx.send(embed=embed_generator('[RAINBOW]',
                                                     'Т.к. роль не была найдена, она была добавлена автоматически!\n'
                                                     'Пожалуйста добавте эту роль, тем кому вы хотите сделать '
                                                     'радужный никнейм :3'))
            except discord.Forbidden:
                await ctx.send(embed=embed_generator('Прав не завезли!',
                                                     f'Добавте боту права "manage_roles" или сами создайте роль '
                                                     f'``{rainbow_role_name}``'))

    @cog_ext.cog_slash(name='choice',
                       description='Выбирает одно из нескольких значений, указанных через запятую')
    async def choice(self, ctx: SlashContext, option: str):
        await ctx.send(f'Я выбираю: {random.choice(option.split(", "))}')

    @cog_ext.cog_slash(name='status',
                       description='Задает текст, который будет отображаться в статусе бота', permissions=perms)
    async def set_status(self, ctx: SlashContext, text: str):
        try:
            config.set('Setting', 'streaming_status_text', text)
            with open('setting.ini', 'w', encoding='utf-8') as configFile:
                config.write(configFile)
            await ctx.send(embed=embed_generator('Успешно!', f'Статус [{text}] был установлен!'))
        except Exception as e:
            await ctx.send(embed=embed_generator('Ашибка!', e))
        self.logger.comm(f'[Status Change] {ctx.author} {text}')


def setup(bot):
    bot.add_cog(Utils(bot))
