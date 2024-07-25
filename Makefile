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
	@bash new_post.sh