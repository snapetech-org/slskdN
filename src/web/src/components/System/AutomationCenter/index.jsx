import { getRegionalLocale } from '../../../lib/regionalFormat';
import {
  automationRecipes,
  buildAutomationExecutionReport,
  buildAutomationRunHistory,
  formatAutomationRunHistoryReport,
  getAutomationRecipeInputs,
  getAutomationRecipeState,
  isAutomationRecipeExecutable,
  setAutomationRecipeInput,
  setAutomationRecipeDryRun,
  setAutomationRecipeEnabled,
  setAutomationRecipeExecution,
} from '../../../lib/automationRecipes';
import { getRunnableWishlistRequests } from '../../../lib/acquisitionRequests';
import * as libraryHealthAPI from '../../../lib/libraryHealth';
import * as wishlistAPI from '../../../lib/wishlist';
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Header,
  Icon,
  Label,
  Message,
  Popup,
  Statistic,
} from 'semantic-ui-react';

const impactColor = (impact) => {
  if (/public/i.test(impact)) {
    return 'orange';
  }

  if (/trusted|metadata|configured|local network/i.test(impact)) {
    return 'blue';
  }

  return 'green';
};

const formatLastDryRun = (value) => {
  if (!value) {
    return 'Not run yet';
  }

  return new Date(value).toLocaleString(getRegionalLocale());
};

const AutomationCenter = () => {
  const [recipeState, setRecipeState] = useState(getAutomationRecipeState);
  const [recipeInputs, setRecipeInputs] = useState(getAutomationRecipeInputs);
  const [copyStatus, setCopyStatus] = useState('');
  const [executingRecipe, setExecutingRecipe] = useState('');
  const summary = useMemo(() => {
    const enabled = automationRecipes.filter(
      (recipe) => recipeState[recipe.id]?.enabled,
    ).length;

    return {
      disabled: automationRecipes.length - enabled,
      enabled,
      total: automationRecipes.length,
    };
  }, [recipeState]);
  const runHistory = useMemo(
    () => buildAutomationRunHistory(recipeState),
    [recipeState],
  );

  const toggleRecipe = (recipe, enabled) => {
    setRecipeState(setAutomationRecipeEnabled(recipe.id, enabled));
    toast.info(`${recipe.title} ${enabled ? 'enabled' : 'disabled'}`);
  };

  const dryRunRecipe = (recipe) => {
    setRecipeState(setAutomationRecipeDryRun(recipe.id));
    toast.info(`${recipe.title} dry run recorded`);
  };

  const executeWishlistRetry = async (recipe) => {
    const allRequests = await wishlistAPI.getAll();
    const runnableRequests = getRunnableWishlistRequests(allRequests, { limit: 3 });
    const result = {
      failed: 0,
      runLimit: 3,
      skipped: Math.max(allRequests.length - runnableRequests.length, 0),
      started: 0,
    };

    for (const request of runnableRequests) {
      try {
        await wishlistAPI.runSearch(request.id);
        result.started += 1;
      } catch {
        result.failed += 1;
      }
    }

    result.summary = `Ran ${result.started} Wishlist searches; ${result.failed} failed; ${result.skipped} skipped.`;
    const report = buildAutomationExecutionReport(recipe, result);
    setRecipeState(setAutomationRecipeExecution(recipe.id, report, report.generatedAt));
    const status = `${recipe.title} ran ${result.started} bounded Wishlist searches; ${result.failed} failed. Downloads still require normal result review.`;
    setCopyStatus(status);
    toast.info(status);
  };

  const executeLibraryHealthScan = async (recipe) => {
    const libraryPath = `${recipeInputs[recipe.id]?.libraryPath || ''}`.trim();
    if (!libraryPath) {
      setCopyStatus('Enter a Library Health path before starting the scan.');
      return;
    }

    const response = await libraryHealthAPI.startScan(libraryPath);
    const scanId = response?.data?.scanId || response?.scanId || 'unknown';
    const report = buildAutomationExecutionReport(recipe, {
      scanId,
      started: 1,
      summary: `Started Library Health scan ${scanId} for ${libraryPath}.`,
    });
    setRecipeState(setAutomationRecipeExecution(recipe.id, report, report.generatedAt));
    const status = `${recipe.title} started scan ${scanId} for ${libraryPath}.`;
    setCopyStatus(status);
    toast.info(status);
  };

  const executeRecipe = async (recipe) => {
    if (!isAutomationRecipeExecutable(recipe)) {
      setCopyStatus(`${recipe.title} does not have a live backend action wired yet.`);
      return;
    }

    setExecutingRecipe(recipe.id);
    try {
      if (recipe.id === 'wishlist-retry') {
        await executeWishlistRetry(recipe);
      }
      if (recipe.id === 'library-health-scan') {
        await executeLibraryHealthScan(recipe);
      }
    } finally {
      setExecutingRecipe('');
    }
  };

  const updateRecipeInput = (recipe, input) => {
    setRecipeInputs(setAutomationRecipeInput(recipe.id, input));
  };

  const copyHistoryReport = async () => {
    const report = formatAutomationRunHistoryReport(runHistory);
    if (!navigator.clipboard?.writeText) {
      setCopyStatus('Clipboard unavailable; copy the automation history manually.');
      return;
    }

    try {
      await navigator.clipboard.writeText(report);
      setCopyStatus('Automation history report copied.');
    } catch {
      setCopyStatus('Unable to copy automation history report.');
    }
  };

  return (
    <div className="automation-center">
      <Header as="h3">
        <Icon name="magic" />
        <Header.Content>
          Automation Center
          <Header.Subheader>
            Every automation is visible here. Enable recipes when their dry-run output and impact fit your node.
          </Header.Subheader>
        </Header.Content>
      </Header>
      <div className="automation-center-actions">
        <Popup
          content="Copy enabled recipes and dry-run checkpoints for operator review. This does not execute any automation."
          position="top center"
          trigger={
            <Button
              aria-label="Copy automation review history"
              onClick={copyHistoryReport}
              size="small"
            >
              <Icon name="copy" />
              Copy History
            </Button>
          }
        />
      </div>
      {copyStatus && (
        <Message
          info
          size="small"
        >
          {copyStatus}
        </Message>
      )}

      <Statistic.Group
        className="automation-summary"
        size="small"
        widths="three"
      >
        <Statistic>
          <Statistic.Value>{summary.total}</Statistic.Value>
          <Statistic.Label>Recipes</Statistic.Label>
        </Statistic>
        <Statistic color="green">
          <Statistic.Value>{summary.enabled}</Statistic.Value>
          <Statistic.Label>Enabled</Statistic.Label>
        </Statistic>
        <Statistic color="orange">
          <Statistic.Value>{summary.disabled}</Statistic.Value>
          <Statistic.Label>Visible Disabled</Statistic.Label>
        </Statistic>
      </Statistic.Group>

      <div className="automation-history-panel">
        <Header as="h4">
          <Icon name="history" />
          Review History
        </Header>
        {runHistory.length === 0 ? (
          <p>No enabled recipes or dry-run checkpoints yet.</p>
        ) : (
          <div className="automation-recipe-labels">
            {runHistory.map((entry) => (
              <Label
                basic
                color={entry.lastRunAt ? 'purple' : entry.lastDryRunAt ? 'green' : 'grey'}
                key={entry.recipeId}
              >
                {entry.title}
                <Label.Detail>
                  {formatLastDryRun(entry.lastRunAt || entry.lastDryRunAt)}
                </Label.Detail>
              </Label>
            ))}
          </div>
        )}
      </div>

      <Card.Group
        className="automation-recipe-grid"
        itemsPerRow={2}
        stackable
      >
        {automationRecipes.map((recipe) => {
          const state = recipeState[recipe.id] ?? {};
          const enabled = state.enabled === true;
          const executable = isAutomationRecipeExecutable(recipe);
          const executing = executingRecipe === recipe.id;
          const libraryHealthPath = recipeInputs[recipe.id]?.libraryPath || '';
          const missingRequiredInput =
            recipe.id === 'library-health-scan' && !libraryHealthPath.trim();

          return (
            <Card
              className="automation-recipe-card"
              key={recipe.id}
            >
              <Card.Content>
                <div className="automation-recipe-head">
                  <Header
                    as="h4"
                    className="automation-recipe-title"
                  >
                    <Icon name={recipe.icon} />
                    <Header.Content>{recipe.title}</Header.Content>
                  </Header>
                  <Popup
                    content={`${enabled ? 'Disable' : 'Enable'} ${recipe.title}. Disabled recipes remain visible so setup work is discoverable.`}
                    position="top center"
                    trigger={
                      <Checkbox
                        aria-label={`${enabled ? 'Disable' : 'Enable'} ${recipe.title}`}
                        checked={enabled}
                        onChange={(_event, { checked }) =>
                          toggleRecipe(recipe, checked)
                        }
                        toggle
                      />
                    }
                  />
                </div>
                <Card.Description>{recipe.description}</Card.Description>
                {recipe.id === 'library-health-scan' && (
                  <Form className="automation-recipe-config">
                    <Form.Input
                      aria-label="Library Health scan path"
                      fluid
                      icon="folder open outline"
                      onChange={(_event, { value }) =>
                        updateRecipeInput(recipe, { libraryPath: value })
                      }
                      placeholder="/music/library"
                      value={libraryHealthPath}
                    />
                  </Form>
                )}
                <div className="automation-recipe-labels">
                  <Label basic>
                    <Icon name="clock outline" />
                    {recipe.cadence}
                  </Label>
                  <Label basic>
                    <Icon name="hourglass half" />
                    Cooldown {recipe.cooldown}
                  </Label>
                  <Label basic>
                    <Icon name="stopwatch" />
                    Max {recipe.maxRunTime}
                  </Label>
                  <Label
                    basic
                    color={impactColor(recipe.networkImpact)}
                  >
                    <Icon name="sitemap" />
                    {recipe.networkImpact}
                  </Label>
                  <Label basic>
                    <Icon name="file outline" />
                    {recipe.fileImpact}
                  </Label>
                  <Label basic>
                    <Icon name="lock" />
                    {recipe.approvalGate}
                  </Label>
                </div>
              </Card.Content>
              <Card.Content extra>
                <div className="automation-recipe-actions">
                  <span className="automation-recipe-dry-run">
                    Dry run: {formatLastDryRun(state.lastDryRunAt)}
                  </span>
                  {state.lastDryRunReport && (
                    <Label
                      basic
                      color="green"
                    >
                      Preview only
                    </Label>
                  )}
                  {state.lastRunReport && (
                    <Label
                      basic
                      color="purple"
                    >
                      Executed
                    </Label>
                  )}
                  <Popup
                    content={`Record a dry run checkpoint for ${recipe.title}. This shell does not execute network or file actions yet.`}
                    position="top center"
                    trigger={
                      <Button
                        aria-label={`Record dry run for ${recipe.title}`}
                        basic
                        icon
                        onClick={() => dryRunRecipe(recipe)}
                        size="small"
                        title={`Record dry run for ${recipe.title}`}
                      >
                        <Icon name="play circle outline" />
                      </Button>
                    }
                  />
                  <Popup
                    content={
                      executable
                        ? `Execute ${recipe.title} now through its real backend action. Wishlist Retry runs up to three enabled searches; Library Health starts the configured read-only scan.`
                        : `No live backend action is wired for ${recipe.title} yet. Use dry run to track readiness.`
                    }
                    position="top center"
                    trigger={
                      <span>
                        <Button
                          aria-label={`Execute ${recipe.title}`}
                          disabled={
                            !enabled ||
                            !executable ||
                            executing ||
                            missingRequiredInput
                          }
                          icon
                          loading={executing}
                          onClick={() => executeRecipe(recipe)}
                          size="small"
                          title={`Execute ${recipe.title}`}
                        >
                          <Icon name="bolt" />
                        </Button>
                      </span>
                    }
                  />
                </div>
              </Card.Content>
            </Card>
          );
        })}
      </Card.Group>
    </div>
  );
};

export default AutomationCenter;
