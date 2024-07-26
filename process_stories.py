import os
import base64
import requests
from pathlib import Path
from openai import OpenAI
import frontmatter
from generate_audio import main as generate_audio

client = OpenAI()


def download_image_to_base64(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def create_story(base64_image):
    story_prompt = """
    Я хочу, чтоб ты рассказал страшилку. Я тебе присылаю фотографию, ты описываешь фотографию, а потом
    на основе этой картинки придумываешь страшилку. Страшную, что-нибудь из городского фольклора,
    городских историй ужасов. Конец не обязательно должен быть хорошим. И дай истории название.

    У истории должно быть 8-12 абзацев.

    Для названий не используй слова как "проклятый", "проклятье", "тайна". Не используй никакое форматирование
    для названия и для текста. Для slug используй короткое называние на английском, такое, которое можно использовать
    в URL.

    Формат:

    Название

    --- 

    slug

    ---

    История
    """

    story_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": story_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
    )

    story_raw = story_response.choices[0].message.content
    title, slug, story = story_raw.split("---")
    return title.strip(), slug.strip(), story.strip()


def create_illustration_prompt(story):
    def extract_first_two_paragraphs(text):
        paragraphs = text.split("\n\n")
        return "\n\n".join(paragraphs[:2])

    first_two_paragraphs = extract_first_two_paragraphs(story)
    prompt = f"""
    На основе текста из истории, создай детальное описание одной сцены на английском, а затем иллюстрацию
    на основе описания. Используй нейтральные обозначения для людей и животных, не имена, например,
    "мальчик" вместо "Ваня", "женщина" вместо "Анна", "собака" вместо "Жучка", и т.п.
    Если в тексте больше одной сцены, выбери только одну, и создай её детальное описание.

    Описание не должно включать в себя последовательность действий, а вместо этого фокусироваться на описании
    одной конкретной сцены.

    Иллюстрация будет использоваться как логотип для эпизода подкаста, поэтому детали должны быть крупным планом
    Не должно быть много объектов, только самые ключевые для описания сцены. Один или два человека, не больше.

    Текст:
    {first_two_paragraphs}

    Стиль иллюстрации:

    a flat, linear style with bold outlines and minimalistic, vibrant colors.
    The scene should include whimsical and slightly eerie elements, such as mountains with skeletal figures,
    simple trees, and small groups of people exploring or interacting with the environment.
    The overall aesthetic should combine a playful cartoonish feel with a touch of spookiness, similar
    to a light-hearted horror theme.

    Avoid adding text on the illustration.

    Only include the resulting prompt for the illustration, don't include the scene description.
    """.strip()

    illustration_prompt = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )

    return illustration_prompt.choices[0].message.content


def generate_illustration(prompt):
    illustration_response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return illustration_response.data[0].url


def get_next_story_id(output_dir):
    existing_files = list(output_dir.glob("*.md"))
    if not existing_files:
        return 1

    max_id = 0
    for file in existing_files:
        content = frontmatter.load(file)
        story_number = int(content.get("story_number", "0"))
        if story_number > max_id:
            max_id = story_number

    return max_id + 1


def save_story(title, slug, story, illustration_url, output_dir, story_id):
    formatted_slug = f"{str(story_id).zfill(3)}-{slug}"
    story_file = Path(output_dir) / f"{formatted_slug}.md"
    post = frontmatter.Post(story)
    post["title"] = title
    post["slug"] = formatted_slug
    post["illustration"] = f"/images/{formatted_slug}.jpg"
    post["story_number"] = str(story_id).zfill(3)
    frontmatter.dump(post, story_file)
    print(f"Saved story: {story_file}")

    # Save illustration to the images folder
    image_folder = Path("images")
    image_folder.mkdir(exist_ok=True)
    illustration_path = image_folder / f"{formatted_slug}.jpg"
    with open(illustration_path, "wb") as f:
        f.write(requests.get(illustration_url).content)
    print(f"Saved illustration: {illustration_path}")


def process_image(image_path, output_dir):
    print(f"Processing image: {image_path}")
    base64_image = download_image_to_base64(image_path)
    title, slug, story = create_story(base64_image)
    illustration_prompt = create_illustration_prompt(story)
    illustration_url = generate_illustration(illustration_prompt)
    story_id = get_next_story_id(output_dir)
    save_story(title, slug, story, illustration_url, output_dir, story_id)
    generate_audio(f"{str(story_id).zfill(3)}-{slug}")


def main():
    input_dir = Path("images_input")
    output_dir = Path("_stories")
    output_dir.mkdir(exist_ok=True)

    for image_file in input_dir.glob("*"):
        if image_file.is_file() and image_file.suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png",
        ]:
            process_image(str(image_file), output_dir)


if __name__ == "__main__":
    main()
