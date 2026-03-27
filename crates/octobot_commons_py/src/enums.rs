use pyo3::prelude::*;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    let enums_mod = py.import("octobot_commons_rs._enums")?;

    // 39 enums from enums.py
    let enum_names = [
        "TimeFrames",
        "TimeFramesMinutes",
        "PriceIndexes",
        "PriceStrings",
        "OptionTypes",
        "PlatformsName",
        "OctoBotTypes",
        "MarkdownFormat",
        "OctoBotChannelSubjects",
        "UserCommands",
        "MultiprocessingLocks",
        "CacheDatabaseTables",
        "CacheDatabaseColumns",
        "PlotAttributes",
        "BacktestingMetadata",
        "DBRows",
        "PlotCharts",
        "DisplayedElementTypes",
        "DBTables",
        "ActivationTopics",
        "TriggerSource",
        "DataBaseOrderBy",
        "DataBaseOperations",
        "RunDatabases",
        "LogicalOperators",
        "CommunityFeedAttrs",
        "CommunityChannelTypes",
        "SignalBundlesAttrs",
        "SignalsAttrs",
        "SignalDependenciesAttrs",
        "InitializationEventExchangeTopics",
        "UserInputTentacleTypes",
        "UserInputTypes",
        "UserInputEditorOptionsTypes",
        "UserInputOtherSchemaValuesTypes",
        "ProfileComplexity",
        "ProfileRisk",
        "ProfileType",
        "SignalHistoryTypes",
        "StopReason",
        // 6 channel name enums
        "OctoBotChannelsName",
        "OctoBotUserChannelsName",
        "OctoBotEvaluatorsChannelsName",
        "OctoBotBacktestingChannelsName",
        "OctoBotCommunityChannelsName",
        "OctoBotTradingChannelsName",
    ];

    for name in enum_names {
        let cls = enums_mod.getattr(name)?;
        m.add(name, &cls)?;
    }

    Ok(())
}
