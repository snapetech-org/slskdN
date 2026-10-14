# Cloudron community package (testing)

This community package is available in Cloudron's **testing** state. It uses
the public Docker Hub image and stores application state, downloads, and the
shared music directory under Cloudron's persistent `/app/data` mount. The
package Dockerfile sets these paths and creates the download and music folders
before starting slskdN.

After the source PR is merged, add the versions URL below under Cloudron's
community apps, or install it with `cloudron install --versions-url <url>`.
Run an install, backup/restore, and update cycle before changing the version
state to `published`.

Versions URL:
`https://raw.githubusercontent.com/snapetech-org/slskdN/main/packaging/cloudron/CloudronVersions.json`
