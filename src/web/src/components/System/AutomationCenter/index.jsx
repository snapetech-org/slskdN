import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
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
  useInterfaceLanguage();
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
    toast.info(interfaceText(enabled ? "{title} enabled" : "{title} disabled", { title: interfaceText(recipe.title) }));
  };

  const dryRunRecipe = (recipe) => {
    setRecipeState(setAutomationRecipeDryRun(recipe.id));
    toast.info(interfaceText("{title} dry run recorded", { title: interfaceText(recipe.title) }));
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
    const status = interfaceText("{title} ran {started} bounded Wishlist searches; {failed} failed. Downloads still require normal result review.", { title: interfaceText(recipe.title), started: result.started, failed: result.failed });
    setCopyStatus(status);
    toast.info(status);
  };

  const executeLibraryHealthScan = async (recipe) => {
    const libraryPath = `${recipeInputs[recipe.id]?.libraryPath || ''}`.trim();
    if (!libraryPath) {
      setCopyStatus(interfaceText('Enter a Library Health path before starting the scan.'));
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
    const status = interfaceText("{title} started scan {scanId} for {libraryPath}.", { title: interfaceText(recipe.title), scanId, libraryPath });
    setCopyStatus(status);
    toast.info(status);
  };

  const executeRecipe = async (recipe) => {
    if (!isAutomationRecipeExecutable(recipe)) {
      setCopyStatus(interfaceText('{title} does not have a live backend action wired yet.', {
        title: interfaceText(recipe.title),
      }));
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
      setCopyStatus(interfaceText('Clipboard unavailable; copy the automation history manually.'));
      return;
    }

    try {
      await navigator.clipboard.writeText(report);
      setCopyStatus(interfaceText('Automation history report copied.'));
    } catch {
      setCopyStatus(interfaceText('Unable to copy automation history report.'));
    }
  };

  return (
    <div className="automation-center">
      <Header as="h3">
        <Icon name="magic" />
        <Header.Content>
          <LocalizedText source={"Automation Center"} /><Header.Subheader>
            <LocalizedText source={"Every automation is visible here. Enable recipes when their dry-run output and impact fit your node."} /></Header.Subheader>
        </Header.Content>
      </Header>
      <div className="automation-center-actions">
        <Popup
          content={interfaceText("Copy enabled recipes and dry-run checkpoints for operator review. This does not execute any automation.")}
          position="top center"
          trigger={
            <Button
              aria-label={interfaceText("Copy automation review history")}
              onClick={copyHistoryReport}
              size="small"
             {...interfaceTextProps("Copy automation review history")}>
              <Icon name="copy" />
              <LocalizedText source={"Copy History"} /></Button>
          }
         {...interfaceTextProps("Copy enabled recipes and dry-run checkpoints for operator review. This does not execute any automation.")}/>
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
          <Statistic.Label><LocalizedText source={"Recipes"} /></Statistic.Label>
        </Statistic>
        <Statistic color="green">
          <Statistic.Value>{summary.enabled}</Statistic.Value>
          <Statistic.Label><LocalizedText source={"Enabled"} /></Statistic.Label>
        </Statistic>
        <Statistic color="orange">
          <Statistic.Value>{summary.disabled}</Statistic.Value>
          <Statistic.Label><LocalizedText source={"Visible Disabled"} /></Statistic.Label>
        </Statistic>
      </Statistic.Group>

      <div className="automation-history-panel">
        <Header as="h4">
          <Icon name="history" />
          <LocalizedText source={"Review History"} /></Header>
        {runHistory.length === 0 ? (
          <p><LocalizedText source={"No enabled recipes or dry-run checkpoints yet."} /></p>
        ) : (
          <div className="automation-recipe-labels">
            {runHistory.map((entry) => (
              <Label
                basic
                color={entry.lastRunAt ? 'purple' : entry.lastDryRunAt ? 'green' : 'grey'}
                key={entry.recipeId}
              >
                {interfaceText(entry.title)}
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
                    <Header.Content><LocalizedText source={recipe.title} /></Header.Content>
                  </Header>
                  <Popup
                    content={interfaceText(enabled ? "Disable {title}. Disabled recipes remain visible so setup work is discoverable." : "Enable {title}. Disabled recipes remain visible so setup work is discoverable.", { title: interfaceText(recipe.title) })}
                    position="top center"
                    trigger={
                      <Checkbox
                        aria-label={interfaceText(enabled ? "Disable {title}" : "Enable {title}", { title: interfaceText(recipe.title) })}
                        checked={enabled}
                        onChange={(_event, { checked }) =>
                          toggleRecipe(recipe, checked)
                        }
                        toggle
                      />
                    }
                  />
                </div>
                <Card.Description><LocalizedText source={recipe.description} /></Card.Description>
                {recipe.id === 'library-health-scan' && (
                  <Form className="automation-recipe-config">
                    <Form.Input
                      aria-label={interfaceText("Library Health scan path")}
                      fluid
                      icon="folder open outline"
                      onChange={(_event, { value }) =>
                        updateRecipeInput(recipe, { libraryPath: value })
                      }
                      placeholder="/music/library"
                      value={libraryHealthPath}
                     {...interfaceTextProps("Library Health scan path")}/>
                  </Form>
                )}
                <div className="automation-recipe-labels">
                  <Label basic>
                    <Icon name="clock outline" />
                    <LocalizedText source={recipe.cadence} />
                  </Label>
                  <Label basic>
                    <Icon name="hourglass half" />
                    <LocalizedText source={"Cooldown"} />{" "}<LocalizedText source={recipe.cooldown} />
                  </Label>
                  <Label basic>
                    <Icon name="stopwatch" />
                    <LocalizedText source={"Max"} />{" "}<LocalizedText source={recipe.maxRunTime} />
                  </Label>
                  <Label
                    basic
                    color={impactColor(recipe.networkImpact)}
                  >
                    <Icon name="sitemap" />
                    <LocalizedText source={recipe.networkImpact} />
                  </Label>
                  <Label basic>
                    <Icon name="file outline" />
                    <LocalizedText source={recipe.fileImpact} />
                  </Label>
                  <Label basic>
                    <Icon name="lock" />
                    <LocalizedText source={recipe.approvalGate} />
                  </Label>
                </div>
              </Card.Content>
              <Card.Content extra>
                <div className="automation-recipe-actions">
                  <span className="automation-recipe-dry-run">
                    <LocalizedText source={"Dry run:"} />{" "}{formatLastDryRun(state.lastDryRunAt)}
                  </span>
                  {state.lastDryRunReport && (
                    <Label
                      basic
                      color="green"
                    >
                      <LocalizedText source={"Preview only"} /></Label>
                  )}
                  {state.lastRunReport && (
                    <Label
                      basic
                      color="purple"
                    >
                      <LocalizedText source={"Executed"} /></Label>
                  )}
                  <Popup
                    content={interfaceText("Record a dry run checkpoint for {title}. This shell does not execute network or file actions yet.", { title: interfaceText(recipe.title) })}
                    position="top center"
                    trigger={
                      <Button
                        aria-label={interfaceText("Record dry run for {title}", { title: interfaceText(recipe.title) })}
                        basic
                        icon
                        onClick={() => dryRunRecipe(recipe)}
                        size="small"
                        title={interfaceText("Record dry run for {title}", { title: interfaceText(recipe.title) })}
                       {...interfaceTextProps("Record dry run for {title}")}>
                        <Icon name="play circle outline" />
                      </Button>
                    }
                   {...interfaceTextProps("Record a dry run checkpoint for {title}. This shell does not execute network or file actions yet.")}/>
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
                          aria-label={interfaceText("Execute {title}", { title: interfaceText(recipe.title) })}
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
                          title={interfaceText("Execute {title}", { title: interfaceText(recipe.title) })}
                         {...interfaceTextProps("Execute {title}")}>
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
