import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import re
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)


class LinkCleaner(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)

        # Comprehensive list of tracking parameters to remove
        self.tracking_params = [
            # UTM parameters
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            # Social media and ad platform tracking
            "fbclid",
            "gclid",
            "ref",
            "source",
            "tk",
            # Affiliate and click tracking
            "aff_id",
            "aff_sub",
            "aff_click_id",
            "click_id",
            # Campaign and ad tracking
            "campaign_id",
            "ad_id",
            "placement_id",
            "creative_id",
            "network_id",
            # Referrer and session tracking
            "utm_referrer",
            "referrer",
            "sref",
            "referer",
            "track_id",
            "tag",
            "subid",
            "subid2",
            "subid3",
            "rurl",
            "sid",
            "dclid",
            "twclid",
            "igshid",
            "igsh",
        ]

        # Regex pattern to find URLs in text
        self.url_pattern = re.compile(r"https?://\S+")

    def is_valid_url(self, url):
        """Validate URL more thoroughly."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def clean_url(self, url):
        """Remove tracking parameters from a URL."""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)

            # Remove tracking parameters
            cleaned_params = {
                key: value
                for key, value in query_params.items()
                if key not in self.tracking_params
            }

            # Reconstruct the URL without tracking parameters
            cleaned_query = urlencode(cleaned_params, doseq=True)
            cleaned_url = urlunparse(
                (
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    parsed_url.params,
                    cleaned_query,
                    parsed_url.fragment,
                )
            )
            return cleaned_url
        except Exception as e:
            logging.error(f"Error cleaning URL {url}: {e}")
            return url

    async def setup_hook(self):
        """Set up the bot, including adding context menu commands"""

        # Add URL cleaning context menu command
        @self.tree.context_menu(name="Clean URL")
        @app_commands.allowed_installs(guilds=True, users=True)
        @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
        async def clean_url_context_menu(
            interaction: discord.Interaction, message: discord.Message
        ):
            # Find URLs in the message
            urls = self.url_pattern.findall(message.content)

            if not urls:
                await interaction.response.send_message(
                    "No URLs found in the message.", ephemeral=True
                )
                return

            cleaned_links = []
            for url in urls:
                # Additional cleaning to remove potential punctuation at end of URL
                url = url.rstrip(".,!?)")

                if self.is_valid_url(url):
                    cleaned_url = self.clean_url(url)
                    # Only add if the URL actually changed
                    if cleaned_url != url:
                        cleaned_links.append(cleaned_url)

            if not cleaned_links:
                await interaction.response.send_message(
                    "No tracking parameters found to clean.", ephemeral=True
                )
                return

            # Create buttons for each cleaned link
            view = discord.ui.View()
            for link in cleaned_links:
                button = discord.ui.Button(label="Open Cleaned Link", url=link)
                view.add_item(button)

            # Send the response with cleaned links and buttons
            cleaned_links_text = "Cleaned links:\n" + "\n".join(cleaned_links)
            await interaction.response.send_message(
                cleaned_links_text, view=view, ephemeral=True
            )

        # Regular message listener for automatic cleaning
        @self.event
        async def on_message(message):
            if message.author.bot:
                return

            # Find all URLs in the message content
            urls = self.url_pattern.findall(message.content)

            cleaned_links = []
            for url in urls:
                # Additional cleaning to remove potential punctuation at end of URL
                url = url.rstrip(".,!?)")

                if self.is_valid_url(url):
                    cleaned_url = self.clean_url(url)
                    # Only add if the URL actually changed
                    if cleaned_url != url:
                        cleaned_links.append(cleaned_url)

            if cleaned_links:
                # Create buttons for each cleaned link
                view = discord.ui.View()
                for link in cleaned_links:
                    button = discord.ui.Button(label="Open Cleaned Link", url=link)
                    view.add_item(button)

                # Send the reply with cleaned links and buttons
                await message.reply(
                    "Here are the cleaned links without tracking:",
                    mention_author=False,
                    view=view,
                )

            # Process commands if needed
            await self.process_commands(message)

        # Sync application commands
        await self.tree.sync()
        logging.info("Bot is ready and commands have been synced.")


def main():
    intents = discord.Intents.default()
    intents.message_content = True

    bot = LinkCleaner(intents)

    # Run the bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))


if __name__ == "__main__":
    main()
