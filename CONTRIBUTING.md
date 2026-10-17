# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change. 

We don't maintain a Contributor License Agreement (CLA) but we do require that anyone that wishes to contribute agrees to the following:

* You have the right to assign the copyright of your contribution.
* By making your contribution, you are giving up copyright of your contribution.

This application is released under the [AGPL 3.0](LICENSE) license, and no single individual or entity owns
or will ever own the copyright.

## slskdn Fork Attribution Policy

[slskdN](https://github.com/snapetech/slskdn) is an unofficial fork of [slskd/slskd](https://github.com/slskd/slskd). We maintain the following copyright attribution policy:

### Existing Files (from upstream slskd)
Files that exist in the upstream repository retain their original copyright:
```csharp
// <copyright file="Example.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
```

### New Files (slskdn-specific)
New files created specifically for slskdn features use the fork's copyright:
```csharp
// <copyright file="Example.cs" company="slskdn Team">
//     Copyright (c) slskdn Team. All rights reserved.
```

### Fork-Specific Directories
The following directories contain slskdn-specific code:
- `src/slskd/Capabilities/` - Peer capability discovery
- `src/slskd/HashDb/` - Local hash database
- `src/slskd/Mesh/` - Epidemic mesh sync protocol
- `src/slskd/Backfill/` - Conservative header probing
- `src/slskd/Transfers/MultiSource/` - Multi-source swarm downloads
- `src/slskd/Transfers/Ranking/` - Source ranking
- `src/slskd/Users/Notes/` - User notes

When creating new files, use the slskdn Team copyright header. When modifying existing upstream files, preserve the original slskd Team copyright.

## Contribution Workflow

1. Assign yourself to the issue that you'll be working on.  If you'd like to contribute something for which there is no 
   existing issue, consider creating one before you start so we can discuss.
1. Clone the repository and `git checkout main` to ensure you are on the default branch.
1. Create a topic branch with `git checkout -b <your-branch-name>` only when current GitHub rules require a pull request.
1. Make your changes. Push the topic branch only when using the pull-request route.
1. Use `main` as the target. Open a pull request only when current GitHub rules require one; push directly when they allow it.
1. Keep the branch current with `main` only when current GitHub rules require it. Merge after the
   checks and approvals required by those rules are satisfied. An explicit maintainer direction to
   merge is sufficient; no additional review or approval is required beyond those rules. Use any
   merge method enabled in GitHub.
1. Delete a completed topic branch when it is no longer needed.

If the pull request needs an update, use `git fetch` and rebase or merge `origin/main` into your branch, then push the updated branch.

## Environment Setup

You'll need [.NET 10.0](https://dotnet.microsoft.com/en-us/download) to build and run the back end (slskd), and you'll
need [Nodejs](https://nodejs.org/en/) to build and debug the front end (web).

You're free to use whichever development tools you prefer.  If you don't yet have a preference, we recommend the following:

[Visual Studio Code](https://code.visualstudio.com/) for front or back end development.

[Visual Studio](https://visualstudio.microsoft.com/downloads/) for back end development.

## Development Setup

### Prerequisites

- **.NET 10.0 SDK**: [Download](https://dotnet.microsoft.com/en-us/download)
- **Node.js 22.22.2+**: [Download](https://nodejs.org/en/)
- **pnpm 12.4.1**: install with Corepack or the pnpm installation guide
- **Git**: For version control
- **IDE**: Visual Studio Code or Visual Studio (recommended)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/snapetech/slskdn.git
   cd slskdn
   ```

2. **Restore dependencies:**
   ```bash
   # Backend
   dotnet restore
   
   # Frontend and Playwright workspace
   pnpm install --frozen-lockfile
   ```

3. **Build the project:**
   ```bash
   dotnet build
   ```

4. **Run tests:**
   ```bash
   dotnet test
   ```

### Development Workflow

1. **Choose a working branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
   Create a feature branch only when current GitHub rules require a pull request; otherwise work on `main`.

2. **Make your changes:**
   - Follow code style guidelines (see below)
   - Write tests for new features
   - Update documentation as needed

3. **Run tests before committing:**
   ```bash
   dotnet test
   ./bin/lint  # Run linter
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

5. **Push and open a PR when current GitHub rules require one:**
   ```bash
   git push origin feature/your-feature-name
   # Open a PR on GitHub only when current rules require it
   ```

## Code Style & Guidelines

### C# Backend

- **File-scoped namespaces**: Use `namespace slskd.Feature;` (C# 10+)
- **Primary constructors**: Use where appropriate (C# 12+)
- **Pattern matching**: Prefer pattern matching over if/else
- **Async/await**: Always use async/await, never `.Result` or `.Wait()`
- **Error handling**: Let errors propagate, don't swallow exceptions
- **Logging**: Use `ILogger<T>`, not `Serilog.Log.ForContext<T>`
- **Dependency injection**: Use constructor injection, not service locator

**Example:**
```csharp
public class MyService : IMyService
{
    private readonly ILogger<MyService> _logger;
    
    public MyService(ILogger<MyService> logger)
    {
        _logger = logger;
    }
    
    public async Task DoWorkAsync()
    {
        try
        {
            await SomeWorkAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to do work");
            throw; // Don't swallow
        }
    }
}
```

### React Frontend

- **Function components**: Use function components with hooks, not class components
- **Hooks**: Use `useState`, `useEffect`, `useCallback`, `useMemo` appropriately
- **Semantic UI**: Use Semantic UI React components
- **Error handling**: Always handle errors in async functions
- **API calls**: Use API library functions, return safe values (empty arrays, not undefined)

**Example:**
```jsx
const MyComponent = ({ prop }) => {
  const [data, setData] = useState([]);
  
  const fetch = async () => {
    try {
      const response = await myLib.getAll();
      setData(Array.isArray(response) ? response : []);
    } catch (error) {
      toast.error(error?.response?.data ?? error?.message ?? error);
    }
  };
  
  useEffect(() => { fetch(); }, []);
  
  return <div>...</div>;
};
```

### Copyright Headers

**New slskdN files:**
```csharp
// <copyright file="MyFile.cs" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>
```

**Existing upstream files:** Keep original `company="slskd Team"` attribution.

**Fork-specific directories** (always use slskdN headers):
- `Capabilities/`, `HashDb/`, `Mesh/`, `Backfill/`
- `Transfers/MultiSource/`, `Transfers/Ranking/`
- `Users/Notes/`, `Wishlist/`

## Testing

### Running Tests

```bash
# All tests
dotnet test

# Specific test project
dotnet test tests/slskd.Tests.Unit/

# Specific test class
dotnet test --filter "FullyQualifiedName~TestClassName"

# With coverage
dotnet test /p:CollectCoverage=true
```

### Writing Tests

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **E2E tests**: Test full workflows (use `SlskdnFullInstanceRunner` for TCP tests)

**Example unit test:**
```csharp
[Fact]
public void MyService_Should_DoSomething()
{
    // Arrange
    var logger = new Mock<ILogger<MyService>>();
    var service = new MyService(logger.Object);
    
    // Act
    var result = service.DoSomething();
    
    // Assert
    Assert.NotNull(result);
}
```

### Test Organization

- **Unit tests**: `tests/slskd.Tests.Unit/`
- **Integration tests**: `tests/slskd.Tests.Integration/`
- **Frontend tests**: `src/web/src/**/*.test.js`

## Debugging

### Back End

Run `./bin/watch` from the root of the repository. This starts the backend in watch mode with hot reload.

**Debug in IDE:**
- Set breakpoints in your IDE
- Attach debugger to running process
- Or run directly from IDE with debug configuration

### Front End

Run `./bin/watch --web` from the root of the directory. Make sure the back end is running first.

**Debug in browser:**
- Open browser DevTools (F12)
- Set breakpoints in Sources tab
- Use React DevTools extension for component inspection

### Common Debugging Scenarios

**Backend not starting:**
- Check logs: `tail -f ~/.config/slskd/logs/slskd.log`
- Verify configuration: `config/slskd.yml`
- Check port availability: `netstat -an | grep 5000`

**Frontend not connecting:**
- Verify backend is running
- Check CORS settings
- Verify API endpoint URLs

**Tests failing:**
- Run tests individually to isolate
- Check test output for specific errors
- Verify test data/fixtures

## Project Structure

```
slskdn/
├── src/
│   ├── slskd/              # Backend C# code
│   │   ├── API/            # API controllers
│   │   ├── Core/           # Core services
│   │   ├── Mesh/           # Mesh networking
│   │   ├── Transfers/      # Download/upload logic
│   │   └── ...
│   └── web/                # Frontend React code
│       ├── src/
│       │   ├── components/ # React components
│       │   ├── lib/        # API client libraries
│       │   └── ...
│       └── package.json
├── tests/                  # Test projects
├── docs/                   # Documentation
├── config/                 # Configuration examples
└── bin/                    # Build scripts
```

## Key Documentation

Before contributing, read:

1. **[memory-bank/decisions/adr-0001-known-gotchas.md](memory-bank/decisions/adr-0001-known-gotchas.md)**: Critical bugs to avoid
2. **[memory-bank/decisions/adr-0002-code-patterns.md](memory-bank/decisions/adr-0002-code-patterns.md)**: Code patterns to follow
3. **[memory-bank/decisions/adr-0003-anti-slop-rules.md](memory-bank/decisions/adr-0003-anti-slop-rules.md)**: What NOT to do
4. **[docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)**: Architecture overview

## Code Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] No linter errors (`./bin/lint`)
- [ ] Copyright headers are correct
- [ ] No hardcoded paths or secrets
- [ ] Error handling is appropriate
- [ ] Logging is meaningful (not spam)
- [ ] No stubs or `NotImplementedException` (create tasks instead)

## Getting Help

- **Discord**: [Join our Discord](https://discord.gg/5PyXBfvS6T)
- **GitHub Issues**: [Open an issue](https://github.com/snapetech/slskdn/issues)
- **Documentation**: See [docs/README.md](docs/README.md)

---

Thank you for contributing to slskdN!
