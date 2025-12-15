"""Discord UI компоненты"""
import discord
import logging
import services.yandex_gpt_art as yandexgptart

class ImageView(discord.ui.View):
    """View с кнопками для сгенерированных изображений"""
    def __init__(self, image_url: str, prompt: str, bot):
        super().__init__(timeout=None)
        self.image_url = image_url
        self.prompt = prompt
        self.bot = bot

    @discord.ui.button(label="Скачать изображение", style=discord.ButtonStyle.green, custom_id="download_image")
    async def download_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Вы можете скачать изображение по [ссылке]({self.image_url}).", ephemeral=True
        )

    @discord.ui.button(label="Скопировать промт", style=discord.ButtonStyle.blurple, custom_id="copy_prompt")
    async def copy_prompt_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Промт для копирования: `{self.prompt}`", ephemeral=True
        )

    @discord.ui.button(label="Сгенерировать снова", style=discord.ButtonStyle.red, row=1, custom_id="regenerate_image")
    async def regenerate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("Генерация изображения, пожалуйста, подождите...", ephemeral=True)
            logging.info(f"Повторная генерация картинки по промту: {self.prompt}")
            new_gpt_img = await yandexgptart.generate_and_save_image(self.prompt, interaction.user.name)
            new_embed = discord.Embed(
                title="Сгенерированное изображение",
                description="Вот изображение, созданное на основе вашего запроса:",
                color=discord.Color.blue()
            )
            new_embed.set_image(url=new_gpt_img)
            new_view = ImageView(new_gpt_img, self.prompt, self.bot)
            await interaction.followup.send(embed=new_embed, view=new_view)
            self.bot.add_view(new_view)
        except Exception as e:
            logging.error(f"Ошибка при повторной генерации изображения: {str(e)}")
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)

