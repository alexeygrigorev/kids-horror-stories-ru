# kids-horror-stories-ru

How it works: https://alexeyondata.substack.com/p/how-i-built-a-fully-automated-image

Страшилки для детей на русском

https://alexeygrigorev.com/kids-horror-stories-ru/


```bash
export S3_BUCKET_IMAGES="kids-horror-stories-ru-images"
uv run python process_stories.py
```

Allowing to push from actions:


```yaml
permissions:
  contents: write
```
