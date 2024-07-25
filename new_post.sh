#!/bin/bash

read -p "Enter the title of the story in Russian: " title_ru
read -p "Enter a short name for the story in English: " title_en

date=$(date +%Y-%m-%d)
slug=$(echo "$title_en" | iconv -t ascii//TRANSLIT | sed -E 's/[^a-zA-Z0-9]+/-/g' | sed -E 's/^-+|-+$//' | tr A-Z a-z)
number=$(printf "%03d" $(ls -1 _stories | wc -l | xargs -I{} expr {} + 1))
file="_stories/$number-$slug.md"

cat << EOF > "$file"
---
layout: story
title: "$title_ru"
date: $date
# illustration: /images/$number-$slug.webp
id: "$number"
---

Write your story here.
EOF

echo "New post created: $file"