# kids-horror-stories-ru

Страшилки для детей на русском


```bash
export S3_BUCKET_IMAGES="kids-horror-stories-ru-images"
pipenv run python process_stories.py
```

Allowing to push from actions:


```yaml
permissions:
  contents: write
```