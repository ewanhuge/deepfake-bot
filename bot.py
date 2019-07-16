import os
from discord.ext import commands
from robot import extract
from robot import queries
from robot import botutils
from robot.db_connection import ConnectionManager
from robot.db_connection import DeepFakeBotConnectionError
from robot.plot_commands import PlotCommands
from robot.model_commands import ModelCommands


class DeepFakeBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def cog_check(self, ctx):
        """Refreshes the database connection and registers the user if not already done."""
        connection_manager = self.bot.get_cog('ConnectionManager')
        try:
            connection_manager.refresh_connection()
        except DeepFakeBotConnectionError:
            await ctx.message.channel.send(
                  'Ruh roh! I seem to be having some issues. Try running that command again later')
            return False

        self.session = connection_manager.session
        queries.register_if_not_already(self.session, ctx)
        return True

    @commands.Cog.listener()
    async def on_ready(self):
        print('Logged in as')
        print(self.bot.user.name)
        print(self.bot.user.id)
        print('------')

    @commands.command()
    async def repeat(self, ctx, msg):
        """Prototype function for testing. Bot will repeat the message in the command."""
        print(msg)
        channel = ctx.message.channel
        await channel.send(msg)

    @commands.command()
    async def extract(self, ctx, *args):
        """Extracts chat history of a subject"""

        try:
            subject_string = args[0]
        except IndexError:
            await ctx.message.channel.send('Usage: `df!extract <User#0000>`')
            return

        subject, error_message = botutils.get_subject(self.bot, ctx, subject_string, 'extract')
        if subject:
            await ctx.message.channel.send(f'Extracting chat history for {subject.name}...')
            self.bot.loop.create_task(
                extract.extract_and_analyze(ctx, subject, self.bot)
            )
        else:
            await ctx.message.channel.send(error_message)

    @commands.command()
    async def reply_as(self, ctx, *args):
        subject_string = args[0]
        subject, error_message = botutils.get_subject(self.bot, ctx, subject_string, 'infer')
        if subject:
            data_uid, job_id = queries.get_latest_model(self.bot.session, ctx, subject)
            if not job_id:
                await ctx.message.channel.send(f'Sorry, I can\'t find a model for {subject_string}')
            else:
                self.bot.loop.create_task(
                    botutils.infer(ctx, data_uid, job_id, self.bot)
                )


app = commands.Bot(command_prefix='df!')
app.add_cog(ConnectionManager(app))
app.add_cog(DeepFakeBot(app))
app.add_cog(PlotCommands(app))
app.add_cog(ModelCommands(app))


@app.event
async def on_message(message):
    await app.process_commands(message)


def run_app():
    token = os.environ.get('DEEPFAKE_DISCORD_TOKEN')
    try:
        app.run(token)
    except RuntimeError as e:
        print('DeepfakeBot: Failed start attempt. I may have already been running.')
        print(e)


if __name__ == '__main__':
    run_app()
