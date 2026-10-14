# Troubleshooting Guide

Common issues and solutions for slskdN.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Download Problems](#download-problems)
- [Performance Issues](#performance-issues)
- [Configuration Problems](#configuration-problems)
- [Web Interface Issues](#web-interface-issues)
- [Feature-Specific Issues](#feature-specific-issues)
- [Getting Additional Help](#getting-additional-help)

## Connection Issues

### Can't Connect to Soulseek

**Symptoms:**
- "Connection failed" error
- "Login failed" error
- Status shows "Disconnected"

**Diagnosis:**
1. Check Soulseek credentials in Settings → Soulseek
2. Verify internet connectivity
3. Check if Soulseek servers are accessible

**Solutions:**

1. **Verify Credentials:**
   ```
   Settings → Soulseek → Username/Password
   ```
   - Ensure username and password are correct
   - Try logging in with official Soulseek client to verify credentials

2. **Check Network Connectivity:**
   ```bash
   # Test connectivity to Soulseek servers
   ping server.slsknet.org
   telnet server.slsknet.org 2234
   ```

3. **Check Firewall:**
   - Ensure port 2234 (Soulseek) is not blocked
   - Check both local firewall and router settings
   - For Docker: ensure ports are properly mapped
   - Also ensure the configured Soulseek listen port is reachable from peers. By default this is `50300/tcp`; if the Web UI works but uploads/downloads stay at `0`, the listen port is often the missing firewall/NAT rule.

4. **Check Soulseek Server Status:**
   - Soulseek servers may be temporarily down
   - Check [Soulseek status](https://www.slsknet.org/) or community forums

5. **Try Different Port:**
   ```yaml
   soulseek:
     listenPort: 2234  # Try different port if 2234 is blocked
   ```

### Can't Connect to Mesh/Pod Network

**Symptoms:**
- Mesh status shows "Disconnected"
- Pod operations fail
- "Mesh not available" errors

**Diagnosis:**
1. Check mesh configuration
2. Verify network connectivity
3. Check mesh gateway settings

**Solutions:**

1. **Check Mesh Configuration:**
   ```yaml
   mesh:
     enabled: true
     gateway:
       enabled: true
       port: 5001
   ```

2. **Check Firewall for Mesh:**
   - Ensure mesh ports are not blocked
   - Check UDP port for DHT (if enabled) — by default this is `50300/udp`, the same port number as the Soulseek listen port (TCP and UDP don't collide). It also carries mesh overlay control and QUIC traffic; see `docs/getting-started.md#first-run-ports`.

3. **Verify Mesh Gateway:**
   - Settings → Mesh → Gateway Status
   - Check if gateway is listening on expected port

4. **Check Logs:**
   ```bash
   # Look for mesh connection errors
   grep -i "mesh" ~/.config/slskd/logs/slskd.log
   ```

## Download Problems

### Downloads Stuck or Not Starting

**Symptoms:**
- Downloads show "Queued" but never start
- Downloads stuck at 0%
- "Connection failed" errors

**Solutions:**

1. **Enable Auto-Replace:**
   - Toggle "Auto-Replace" in Downloads header
   - slskdN will automatically find alternatives

2. **Check Peer Status:**
   - User may be offline
   - User may have no free upload slots
   - User may have rejected the download

3. **Check Queue Position:**
   - Some users have long queues
   - Wait time depends on queue position
   - Consider finding alternative sources

4. **Try Swarm Download:**
   - Multiple sources improve reliability
   - Enable in Settings → Features → Swarm Downloads

5. **Check Download Directory:**
   - Ensure download directory exists and is writable
   - Check disk space: `df -h` (Linux/macOS)

### Downloads Very Slow

**Symptoms:**
- Downloads progressing but very slowly
- Speed much lower than expected

**Solutions:**

1. **Check Peer Upload Speed:**
   - Some peers have slow upload speeds
   - Try finding peers with better speeds

2. **Enable Swarm Downloads:**
   - Multiple sources can improve speed
   - Settings → Features → Swarm Downloads

3. **Check Network:**
   - Test internet speed
   - Check for network congestion
   - Verify no bandwidth limits

4. **Adjust Concurrent Downloads:**
   ```yaml
   downloads:
     maxConcurrent: 5  # Reduce if network is slow
   ```

5. **Check for Throttling:**
   - Some ISPs throttle P2P traffic
   - Consider using VPN if throttling detected

### Downloads Failing with Errors

**Symptoms:**
- Downloads fail immediately
- Error messages in download status
- "File not found" or "Access denied" errors

**Solutions:**

1. **Check File Availability:**
   - File may have been removed by user
   - User may have changed share settings

2. **Try Alternative Sources:**
   - Use Auto-Replace feature
   - Search for file again to find other sources

3. **Check Share Settings:**
   - User may have restricted access
   - File may be in private share

4. **Verify File Size:**
   - File size mismatch may indicate file changed
   - Try downloading again

## Performance Issues

### High CPU Usage

**Symptoms:**
- slskdN using excessive CPU
- System becomes slow
- CPU usage >50% constantly

**Solutions:**

1. **Reduce Concurrent Downloads:**
   ```yaml
   downloads:
     maxConcurrent: 3  # Reduce from default
   ```

2. **Disable Background Features:**
   - Disable Wishlist if not needed
   - Disable Auto-Replace if not needed
   - Reduce search result limits

3. **Check for Stuck Processes:**
   - Restart slskdN
   - Check for hung downloads

4. **Review Logs:**
   ```bash
   # Look for errors or warnings
   tail -f ~/.config/slskd/logs/slskd.log
   ```

### High Memory Usage

**Symptoms:**
- slskdN using excessive memory
- System running out of memory
- Memory usage >1GB

**Solutions:**

1. **Reduce Search Result Limits:**
   ```yaml
   search:
     maxResults: 1000  # Reduce from default
   ```

2. **Clear Search History:**
   - Click "Clear All" in Search interface
   - Old searches consume memory

3. **Restart Periodically:**
   - Memory leaks may accumulate over time
   - Schedule periodic restarts

4. **Check for Memory Leaks:**
   - Monitor memory usage over time
   - Report if memory grows continuously

### Slow Search Results

**Symptoms:**
- Searches take very long
- Results appear slowly
- Search times out

**Solutions:**

1. **Adjust Search Timeout:**
   ```yaml
   search:
     timeout: 30000  # Increase timeout (milliseconds)
   ```

2. **Reduce Search Scope:**
   - Use more specific search terms
   - Apply filters to narrow results

3. **Check Network:**
   - Slow network affects search speed
   - Check for network issues

4. **Disable Unused Sources:**
   - Disable Pod/Mesh if not needed
   - Focus on single source for faster results

## Configuration Problems

### Configuration Not Saving

**Symptoms:**
- Settings changes not persisting
- Configuration reverts after restart
- "Permission denied" errors

**Solutions:**

1. **Check File Permissions:**
   ```bash
   # Linux/macOS
   ls -la ~/.config/slskd/config/slskd.yml
   chmod 644 ~/.config/slskd/config/slskd.yml
   ```

2. **Check Directory Permissions:**
   - Ensure config directory is writable
   - Check parent directory permissions

3. **Check for Syntax Errors:**
   - YAML syntax errors prevent saving
   - Validate YAML syntax
   - Check logs for parsing errors

4. **Use Web UI:**
   - Web UI validates input
   - Prevents invalid configurations

### Invalid Configuration Errors

**Symptoms:**
- "Invalid configuration" errors at startup
- Service fails to start
- Configuration validation errors

**Solutions:**

1. **Validate YAML Syntax:**
   ```bash
   # Use online YAML validator or
   python -c "import yaml; yaml.safe_load(open('config/slskd.yml'))"
   ```

2. **Check Configuration Reference:**
   - See [Configuration Reference](config.md)
   - Verify all options are valid

3. **Reset to Defaults:**
   - Backup current config
   - Start with minimal config
   - Add options incrementally

4. **Check Logs:**
   ```bash
   # Look for specific validation errors
   grep -i "config" ~/.config/slskd/logs/slskd.log
   ```

## Web Interface Issues

### Web Interface Not Loading

**Symptoms:**
- Can't access `http://localhost:5000`
- "Connection refused" error
- Blank page

**Solutions:**

1. **Check if Service is Running:**
   ```bash
   # Linux/macOS
   ps aux | grep slskdn
   
   # Windows
   # Check Task Manager
   ```

2. **Check Port:**
   ```bash
   # Check if port 5000 is in use
   netstat -an | grep 5000
   lsof -i :5000
   ```

3. **Check Firewall:**
   - Ensure port 5000 is not blocked
   - Check local firewall settings

4. **Try Different Port:**
   ```yaml
   web:
     port: 5001  # Change if 5000 is in use
   ```

5. **Check Logs:**
   ```bash
   # Look for web server errors
   tail -f ~/.config/slskd/logs/slskd.log | grep -i web
   ```

### Web Interface Slow or Unresponsive

**Symptoms:**
- Web UI loads slowly
- Buttons don't respond
- Interface freezes

**Solutions:**

1. **Clear Browser Cache:**
   - Clear browser cache and cookies
   - Try incognito/private mode

2. **Check Browser:**
   - Use modern browser (Chrome, Firefox, Edge)
   - Update browser to latest version

3. **Reduce Data Load:**
   - Close unused tabs
   - Reduce search result limits
   - Clear old searches

4. **Check Network:**
   - Slow network affects WebSocket connections
   - Check for network issues

### Authentication Issues

**Symptoms:**
- Can't log in
- "Invalid credentials" error
- Session expires immediately

**Solutions:**

1. **Reset Password:**
   - Use command-line option: `--reset-password`
   - Or delete auth database and restart

2. **Check Authentication Method:**
   ```yaml
   web:
     authentication:
       method: "cookie"  # or "jwt"
   ```

3. **Clear Browser Data:**
   - Clear cookies for localhost:5000
   - Try different browser

4. **Check Logs:**
   ```bash
   # Look for authentication errors
   grep -i "auth" ~/.config/slskd/logs/slskd.log
   ```

## Feature-Specific Issues

### Chromaprint Fingerprint Attempts Fail

**Symptoms:**
- Metadata processing shows `chromaprint` as failed after a completed audio download
- Logs contain `Fingerprint extraction failed`
- AcoustID lookups do not occur for the affected file

**Diagnosis:**
1. Open System -> Integrations and inspect the metadata-processing result. The
   failure detail includes the exception and, for decoder failures, ffmpeg's
   stderr output.
2. Confirm that Chromaprint is enabled only if fingerprinting is wanted:
   ```yaml
   integrations:
     chromaprint:
       enabled: true
       ffmpeg_path: ffmpeg
   ```
3. Test the configured decoder from the same environment that runs slskdN:
   ```bash
   ffmpeg -hide_banner -version
   ```
4. If the configured path is not `ffmpeg`, verify that exact path is executable
   and that the slskdN process can read the completed audio file.
5. Check that the native Chromaprint library is installed. Docker's standard
   image includes it; host installations must provide `libchromaprint`,
   `chromaprint.dll`, or `libchromaprint.dylib` on the native library path.

The common error `StandardError has not been redirected` is an application
ordering error from older builds, not evidence that the audio release is bad.
Current builds start ffmpeg before opening its redirected streams and retain
the actual decoder diagnostic when a file cannot be decoded.

### HTTPS Login Shows a Network Error

If Firefox or LibreWolf reports repeated messages such as:

```text
Cookie XSRF-COOKIE-5030 has been rejected because there is an existing secure cookie
```

the same host has usually been opened through both HTTP and HTTPS. Cookies are
host-scoped, not port-scoped or scheme-scoped, so the two listeners were
competing over the same antiforgery cookie name. Current builds mark these
cookies `Secure` on HTTPS and do not mint them from HTTP, preventing the HTTP
listener from replacing the HTTPS cookie. If HTTPS is intentionally disabled,
the HTTP-only deployment uses non-secure cookies as expected.

For an existing browser profile, close the affected tabs and clear site data
for the slskdN host once, then open the HTTPS URL directly. If login still
shows a network error, use the browser's certificate warning page to trust the
configured certificate, or configure a trusted PFX certificate under
`web.https.certificate.pfx` and restart slskdN. A self-signed certificate can
also be valid but still rejected by the browser for API requests until its
exception is accepted.

### Live UI Shows Disconnected With an API Key

If REST API calls work with `X-API-Key` but the browser shows `Disconnected`
and the console reports 401 responses from `/hub/application/negotiate`,
`/hub/search/negotiate`, or `/hub/transfers/negotiate`, the server is likely an
older build that does not promote SignalR query tokens. Current builds support
the API key in both REST headers and SignalR's `access_token` query parameter.
Verify the running version under System -> Info and upgrade to the current
release. Do not put an API key in a normal URL or share it in browser history.

### Automatic Downloads Continue After Cancellation

Auto-replace is intended only for transfers that ended because of a timeout,
error, or peer rejection. Current builds do not treat a user-cancelled transfer
as stuck, and disabling Auto-replace cancels the active replacement cycle.

Wishlist auto-download also refuses a single peer directory when it contains
more than 50 unique track names. Numeric duplicate suffixes such as `(1)` and
`(2)` are normalized to the same track identity. This prevents malformed or
overly broad releases from enqueueing hundreds of files automatically. Use the
manual search result to inspect unusually large releases.

### Swarm Downloads Not Working

**Symptoms:**
- Swarm downloads not starting
- "Not enough sources" errors
- Swarm visualization not showing

**Solutions:**

1. **Enable Swarm Feature:**
   ```yaml
   feature:
     MultiSourceDownloads: true
   ```

2. **Check Source Count:**
   - Need at least 2 verified sources
   - Verify sources have matching content

3. **Check Chunk Size:**
   - Very small files may not benefit from swarming
   - Adjust chunk size if needed

4. **View Swarm Status:**
   - System → Jobs → View Details on swarm job
   - Check for errors in visualization

### Wishlist Not Running

**Symptoms:**
- Wishlist searches not executing
- No results from background searches
- "Wishlist disabled" message

**Solutions:**

1. **Enable Wishlist:**
   ```yaml
   wishlist:
     enabled: true
     interval_seconds: 3600  # Run every hour; minimum 300
   ```

2. **Check Search Configuration:**
   - Verify search query is valid
   - Check filters aren't too restrictive

3. **Check Logs:**
   ```bash
   # Look for wishlist errors
   grep -i "wishlist" ~/.config/slskd/logs/slskd.log
   ```

### Collections Not Sharing

**Symptoms:**
- Can't share collections
- "Permission denied" errors
- Shares not visible to others

**Solutions:**

1. **Enable Collections Feature:**
   ```yaml
   feature:
     CollectionsSharing: true
   ```

2. **Check Share Policy:**
   - Verify share policy allows access
   - Check user permissions

3. **Check Mesh Connectivity:**
   - Verify the collection/share source is available to this instance

### Streaming Not Working

**Symptoms:**
- Stream button not available
- Stream fails to start
- "Streaming not supported" error

**Solutions:**

1. **Enable Streaming Feature:**
   ```yaml
   feature:
     Streaming: true
   ```

2. **Check Content Source:**
   - Streaming requires an accessible local, peer, Pod, or Mesh content source

3. **Check Download Status:**
   - Content must be downloading or downloaded
   - Can't stream content that's not available

## Getting Additional Help

### Check Logs

**Log Locations:**
- Linux/macOS: `~/.config/slskd/logs/slskd.log`
- Windows: `%APPDATA%\slskd\logs\slskd.log`
- Docker: `docker logs slskdn`

**Useful Log Commands:**
```bash
# View recent errors
tail -100 ~/.config/slskd/logs/slskd.log | grep -i error

# Monitor logs in real-time
tail -f ~/.config/slskd/logs/slskd.log

# Search for specific issues
grep -i "connection" ~/.config/slskd/logs/slskd.log
```

### Enable Debug Logging

**Temporary Debug Mode:**
```yaml
logging:
  levels:
    slskd: Debug
    slskd.Transfers: Debug
    slskd.Mesh: Debug
```

**Note:** Debug logging generates large log files. Disable after troubleshooting.

### Community Resources

1. **Discord**: [Join our Discord](https://discord.gg/5PyXBfvS6T)
   - Real-time help from community
   - Share issues and solutions

2. **GitHub Issues**: [Report Issues](https://github.com/snapetech-org/slskdN/issues)
   - Bug reports
   - Feature requests
   - Include logs and configuration (redact sensitive info)

3. **Documentation**:
   - [Getting Started](getting-started.md)
   - [Configuration Reference](config.md)
   - [Features Overview](FEATURES.md)
   - [Known Issues](known_issues.md)

### Reporting Issues

When reporting issues, include:

1. **Version**: `slskdn --version` or check About page
2. **Operating System**: OS and version
3. **Configuration**: Relevant config sections (redact sensitive info)
4. **Logs**: Relevant log excerpts (last 50-100 lines)
5. **Steps to Reproduce**: Detailed steps to trigger the issue
6. **Expected vs Actual**: What should happen vs what actually happens

### Professional Support

For enterprise deployments or complex issues:
- Review [Security Guidelines](SECURITY-GUIDELINES.md)
- Check [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md) for feature status
- Consider professional consulting for custom configurations

---

**Still having issues?** Join our [Discord](https://discord.gg/5PyXBfvS6T) or [open an issue](https://github.com/snapetech-org/slskdN/issues)!
