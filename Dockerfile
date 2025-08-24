# Make sure RUBY_VERSION matches the Ruby version in .ruby-version and Gemfile
ARG RUBY_VERSION=3.4.4

# FROM registry.docker.com/library/ruby:$RUBY_VERSION-slim AS base
FROM docker.m.daocloud.io/library/ruby:$RUBY_VERSION-slim AS base

# Rails app lives here
WORKDIR /rails

# Allow overriding APT mirror at build time (default is official Debian mirror)
ARG APT_MIRROR="http://mirrors.ustc.edu.cn/debian"
ARG APT_SECURITY_MIRROR="http://mirrors.ustc.edu.cn/debian-security"

# Install base packages. Some slim images don't have /etc/apt/sources.list, so
# guard the backup and write a temporary sources file instead of failing.
RUN set -eux; \
    # Write a minimal /etc/apt/sources.list directly using the provided mirror and suite 'bookworm'.
    # This avoids sed/cp failures when the base image doesn't contain a sources.list.
    printf '%s\n' \
        "deb ${APT_MIRROR} bookworm main" \
        "deb ${APT_MIRROR} bookworm-updates main" \
        "deb ${APT_SECURITY_MIRROR} bookworm-security main" > /etc/apt/sources.list; \
    # Remove any additional sources that could point to the official mirror
    rm -f /etc/apt/sources.list.d/* || true; \
    echo '=== /etc/apt directory listing ==='; ls -la /etc/apt || true; \
    echo '=== /etc/apt/sources.list ==='; cat /etc/apt/sources.list || true; \
    apt-get update -qq; \
    apt-get install --no-install-recommends -y curl libvips postgresql-client libyaml-0-2; 

# Set production environment
ARG BUILD_COMMIT_SHA
ENV RAILS_ENV="production" \
    BUNDLE_DEPLOYMENT="1" \
    BUNDLE_PATH="/usr/local/bundle" \
    BUNDLE_WITHOUT="development" \
    BUILD_COMMIT_SHA=${BUILD_COMMIT_SHA}
    
# Throw-away build stage to reduce size of final image
FROM base AS build

# Install packages needed to build gems
RUN apt-get install --no-install-recommends -y build-essential libpq-dev git pkg-config libyaml-dev

# Configure github proxy
RUN git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"

# Install application gems
COPY .ruby-version Gemfile Gemfile.lock ./
# If the repo includes a prepackaged vendor/cache (from `bundle package --all`),
# copy it into the image and prefer a local install to avoid network access.
# COPY vendor/cache vendor/cache
RUN bundle config set --local deployment 'true' \
 && bundle config set --local without 'development test' \
 && if [ -d vendor/cache ]; then \
            bundle install --local --jobs 4; \
        else \
            bundle install --jobs 4; \
        fi

RUN rm -rf ~/.bundle/ "${BUNDLE_PATH}"/ruby/*/cache "${BUNDLE_PATH}"/ruby/*/bundler/gems/*/.git

RUN bundle exec bootsnap precompile --gemfile -j 0

# Copy application code
COPY . .

# Precompile bootsnap code for faster boot times
RUN bundle exec bootsnap precompile -j 0 app/ lib/

# Precompiling assets for production without requiring secret RAILS_MASTER_KEY
RUN SECRET_KEY_BASE_DUMMY=1 ./bin/rails assets:precompile

# Final stage for app image
FROM base

# Clean up installation packages to reduce image size
RUN rm -rf /var/lib/apt/lists /var/cache/apt/archives

# Copy built artifacts: gems, application
COPY --from=build "${BUNDLE_PATH}" "${BUNDLE_PATH}"
COPY --from=build /rails /rails

# Run and own only the runtime files as a non-root user for security
RUN groupadd --system --gid 1000 rails && \
    useradd rails --uid 1000 --gid 1000 --create-home --shell /bin/bash && \
    chown -R rails:rails db log storage tmp
USER 1000:1000

# Entrypoint prepares the database.
ENTRYPOINT ["/rails/bin/docker-entrypoint"]

# Start the server by default, this can be overwritten at runtime
EXPOSE 3000
CMD ["./bin/rails", "server"]
