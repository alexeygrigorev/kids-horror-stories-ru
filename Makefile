# Makefile for Jekyll website

.PHONY: serve build clean deploy install update new_post ensure_bundler

# Ensure Bundler is installed
ensure_bundler:
	@which bundle > /dev/null || gem install bundler

# Run Jekyll locally
serve: ensure_bundler
	bundle exec jekyll serve

# Build the site
build: ensure_bundler
	bundle exec jekyll build

# Clean the site
clean: ensure_bundler
	bundle exec jekyll clean

# Deploy to GitHub Pages (assumes you're using the gh-pages branch)
deploy:
	git checkout gh-pages
	git merge main
	git push origin gh-pages
	git checkout main

# Install dependencies
install: ensure_bundler
	bundle install

# Update dependencies
update: ensure_bundler
	bundle update

# Create a new post
new_post:
	@read -p "Enter the title of the new post: " title; \
	date=$$(date +%Y-%m-%d); \
	slug=$$(echo "$$title" | iconv -t ascii//TRANSLIT | sed -E 's/[^a-zA-Z0-9]+/-/g' | sed -E 's/^-+|-+$$//g' | tr A-Z a-z); \
	number=$$(printf "%03d" $$(ls -1 _stories | wc -l | xargs -I{} expr {} + 1)); \
	echo "---\nlayout: story\ntitle: \"$$title\"\ndate: $$date\nillustration: /assets/images/$$number-$$slug.jpg\nid: \"$$number\"\n---\n\nWrite your story here." > "_stories/$$number-$$slug.md"; \
	echo "New post created: _stories/$$number-$$slug.md"