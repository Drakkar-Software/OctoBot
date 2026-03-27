#[macro_export]
macro_rules! str_enum {
    (
        $(#[$meta:meta])*
        pub enum $name:ident {
            $( $variant:ident => $val:expr ),+ $(,)?
        }
    ) => {
        $(#[$meta])*
        #[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
        pub enum $name {
            $( $variant ),+
        }

        impl $name {
            pub fn value(self) -> &'static str {
                match self {
                    $( Self::$variant => $val ),+
                }
            }

            pub fn from_value(v: &str) -> Option<Self> {
                match v {
                    $( $val => Some(Self::$variant), )+
                    _ => None,
                }
            }

            pub fn variants() -> &'static [Self] {
                &[ $( Self::$variant ),+ ]
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str(self.value())
            }
        }
    };
}

#[macro_export]
macro_rules! int_enum {
    (
        $(#[$meta:meta])*
        pub enum $name:ident {
            $( $variant:ident => $val:expr ),+ $(,)?
        }
    ) => {
        $(#[$meta])*
        #[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
        pub enum $name {
            $( $variant ),+
        }

        impl $name {
            pub fn value(self) -> i64 {
                match self {
                    $( Self::$variant => $val ),+
                }
            }

            pub fn from_value(v: i64) -> Option<Self> {
                match v {
                    $( $val => Some(Self::$variant), )+
                    _ => None,
                }
            }

            pub fn variants() -> &'static [Self] {
                &[ $( Self::$variant ),+ ]
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                write!(f, "{}", self.value())
            }
        }
    };
}

// ---------------------------------------------------------------------------
// TimeFrames
// ---------------------------------------------------------------------------

str_enum! {
    pub enum TimeFrames {
        OneMinute => "1m",
        ThreeMinutes => "3m",
        FiveMinutes => "5m",
        FifteenMinutes => "15m",
        ThirtyMinutes => "30m",
        OneHour => "1h",
        TwoHours => "2h",
        ThreeHours => "3h",
        FourHours => "4h",
        SixHours => "6h",
        EightHours => "8h",
        TwelveHours => "12h",
        OneDay => "1d",
        ThreeDays => "3d",
        OneWeek => "1w",
        OneMonth => "1M",
        OneYear => "1y",
    }
}

pub fn time_frames_minutes(tf: TimeFrames) -> u32 {
    match tf {
        TimeFrames::OneMinute => 1,
        TimeFrames::ThreeMinutes => 3,
        TimeFrames::FiveMinutes => 5,
        TimeFrames::FifteenMinutes => 15,
        TimeFrames::ThirtyMinutes => 30,
        TimeFrames::OneHour => 60,
        TimeFrames::TwoHours => 120,
        TimeFrames::ThreeHours => 180,
        TimeFrames::FourHours => 240,
        TimeFrames::SixHours => 360,
        TimeFrames::EightHours => 480,
        TimeFrames::TwelveHours => 720,
        TimeFrames::OneDay => 1440,
        TimeFrames::ThreeDays => 4320,
        TimeFrames::OneWeek => 10080,
        TimeFrames::OneMonth => 43200,
        TimeFrames::OneYear => 524160,
    }
}

// ---------------------------------------------------------------------------
// PriceIndexes
// ---------------------------------------------------------------------------

int_enum! {
    pub enum PriceIndexes {
        IndPriceTime => 0,
        IndPriceOpen => 1,
        IndPriceHigh => 2,
        IndPriceLow => 3,
        IndPriceClose => 4,
        IndPriceVol => 5,
    }
}

// ---------------------------------------------------------------------------
// PriceStrings
// ---------------------------------------------------------------------------

str_enum! {
    pub enum PriceStrings {
        StrPriceTime => "time",
        StrPriceClose => "close",
        StrPriceOpen => "open",
        StrPriceHigh => "high",
        StrPriceLow => "low",
        StrPriceVol => "vol",
    }
}

// ---------------------------------------------------------------------------
// OptionTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum OptionTypes {
        Put => "P",
        Call => "C",
    }
}

// ---------------------------------------------------------------------------
// PlatformsName
// ---------------------------------------------------------------------------

str_enum! {
    pub enum PlatformsName {
        Windows => "nt",
        Linux => "posix",
        Mac => "mac",
    }
}

// ---------------------------------------------------------------------------
// OctoBotTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum OctoBotTypes {
        Binary => "binary",
        Python => "python",
        Docker => "docker",
    }
}

// ---------------------------------------------------------------------------
// MarkdownFormat — mixed int/string values
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum MarkdownFormat {
    Italic,
    Bold,
    Code,
    Ignore,
    None,
}

impl MarkdownFormat {
    pub fn str_value(self) -> Option<&'static str> {
        match self {
            Self::Italic => Some("_"),
            Self::Bold => Some("*"),
            Self::Code => Some("`"),
            Self::Ignore => Option::None,
            Self::None => Option::None,
        }
    }

    pub fn int_value(self) -> Option<i64> {
        match self {
            Self::Ignore => Some(1),
            Self::None => Some(0),
            Self::Italic | Self::Bold | Self::Code => Option::None,
        }
    }
}

// ---------------------------------------------------------------------------
// OctoBotChannelSubjects
// ---------------------------------------------------------------------------

str_enum! {
    pub enum OctoBotChannelSubjects {
        Notification => "notification",
        Creation => "creation",
        Update => "update",
        Deletion => "deletion",
        Error => "error",
    }
}

// ---------------------------------------------------------------------------
// UserCommands
// ---------------------------------------------------------------------------

str_enum! {
    pub enum UserCommands {
        ManualTrigger => "manual_trigger",
        OptimizeInitialPortfolio => "optimize_initial_portfolio",
        TriggerHealthCheck => "trigger_health_check",
        ReloadConfig => "reload_config",
        ReloadScript => "reload_script",
        ClearPlottingCache => "clear_plotting_cache",
        ClearSimulatedOrdersCache => "clear_simulated_orders_cache",
        ClearSimulatedTradesCache => "clear_simulated_trades_cache",
        ClearSimulatedTransactionsCache => "clear_simulated_transactions_cache",
    }
}

// ---------------------------------------------------------------------------
// MultiprocessingLocks
// ---------------------------------------------------------------------------

str_enum! {
    pub enum MultiprocessingLocks {
        DbLock => "db_lock",
    }
}

// ---------------------------------------------------------------------------
// CacheDatabaseTables
// ---------------------------------------------------------------------------

str_enum! {
    pub enum CacheDatabaseTables {
        Cache => "cache",
        Metadata => "metadata",
    }
}

// ---------------------------------------------------------------------------
// CacheDatabaseColumns
// ---------------------------------------------------------------------------

str_enum! {
    pub enum CacheDatabaseColumns {
        Timestamp => "t",
        Value => "v",
        Type => "ty",
        TriggeredAfterCandlesClose => "triggered_after_candles_close",
    }
}

// ---------------------------------------------------------------------------
// PlotAttributes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum PlotAttributes {
        Kind => "kind",
        X => "x",
        Y => "y",
        Z => "z",
        Open => "open",
        High => "high",
        Low => "low",
        Close => "close",
        Volume => "volume",
        Title => "title",
        Text => "text",
        SubElements => "sub_elements",
        Elements => "elements",
        Name => "name",
        Data => "data",
        XType => "x_type",
        YType => "y_type",
        Mode => "mode",
        LineShape => "line_shape",
        OwnXaxis => "own_xaxis",
        OwnYaxis => "own_yaxis",
        Side => "side",
        Value => "value",
        Config => "config",
        Schema => "schema",
        Tentacle => "tentacle",
        TentacleType => "tentacle_type",
        Columns => "columns",
        Rows => "rows",
        Searches => "searches",
        IsHidden => "is_hidden",
        Type => "type",
        Color => "color",
        Html => "html",
        Size => "size",
        Shape => "shape",
        Symbol => "symbol",
    }
}

// ---------------------------------------------------------------------------
// BacktestingMetadata
// ---------------------------------------------------------------------------

str_enum! {
    pub enum BacktestingMetadata {
        Id => "id",
        Gains => "gains",
        PercentGains => "% gains",
        MarketsProfitability => "markets profitability",
        EndPortfolio => "end portfolio",
        StartPortfolio => "start portfolio",
        WinRate => "% win rate",
        DrawDown => "% draw down",
        CoefficientOfDeterminationMaxBalance => "R\u{b2} max balance",
        CoefficientOfDeterminationEndBalance => "R\u{b2} end balance",
        Symbols => "symbols",
        TimeFrames => "time frames",
        StartTime => "start time",
        EndTime => "end time",
        Duration => "duration",
        Entries => "entries",
        Wins => "wins",
        Loses => "loses",
        Trades => "trades",
        Timestamp => "timestamp",
        Name => "name",
        Leverage => "leverage",
        OptimizationCampaign => "optimization campaign",
        UserInputs => "user inputs",
        BacktestingFiles => "backtesting files",
        Children => "children",
        OptimizerId => "optimizer id",
        Exchange => "exchange",
    }
}

// ---------------------------------------------------------------------------
// DBRows
// ---------------------------------------------------------------------------

str_enum! {
    pub enum DBRows {
        Id => "id",
        ReferenceMarket => "ref_market",
        Exchange => "exchange",
        Exchanges => "exchanges",
        FutureContracts => "future_contracts",
        Pair => "pair",
        TimeFrame => "time_frame",
        Value => "value",
        StartTime => "start_time",
        EndTime => "end_time",
        TradingType => "trading_type",
        TradingMode => "trading_mode",
        Symbol => "symbol",
        Symbols => "symbols",
        FeesAmount => "fees_amount",
        FeesCurrency => "fees_currency",
    }
}

// ---------------------------------------------------------------------------
// PlotCharts
// ---------------------------------------------------------------------------

str_enum! {
    pub enum PlotCharts {
        MainChart => "main-chart",
        SubChart => "sub-chart",
    }
}

// ---------------------------------------------------------------------------
// DisplayedElementTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum DisplayedElementTypes {
        Chart => "chart",
        Input => "input",
        Table => "table",
        Value => "value",
        Dictionary => "dictionary",
    }
}

// ---------------------------------------------------------------------------
// DBTables
// ---------------------------------------------------------------------------

str_enum! {
    pub enum DBTables {
        Metadata => "metadata",
        Inputs => "inputs",
        Portfolio => "portfolio",
        Orders => "all_orders",
        HistoricalOrdersUpdates => "order_updates",
        Trades => "all_trades",
        Transactions => "all_transactions",
        Candles => "candles",
        CandlesSource => "candles_source",
        CacheSource => "cache_source",
    }
}

// ---------------------------------------------------------------------------
// ActivationTopics
// ---------------------------------------------------------------------------

str_enum! {
    pub enum ActivationTopics {
        FullCandles => "once per bar close",
        InConstructionCandles => "once per second (Live Price)",
        RecentTrades => "recent trades",
        EvaluationCycle => "after evaluators",
    }
}

// ---------------------------------------------------------------------------
// TriggerSource
// ---------------------------------------------------------------------------

str_enum! {
    pub enum TriggerSource {
        Initialization => "initialization",
        EvaluationMatrix => "evaluation_matrix",
        EvaluatorRefresh => "evaluator_refresh",
        Ohlcv => "ohlcv",
        Kline => "kline",
        Order => "order",
        Trade => "trade",
        Price => "price",
        Balance => "balance",
        Position => "position",
        ConfigurationUpdate => "configuration_update",
        Manual => "manual",
        Undefined => "undefined",
    }
}

// ---------------------------------------------------------------------------
// DataBaseOrderBy
// ---------------------------------------------------------------------------

str_enum! {
    pub enum DataBaseOrderBy {
        Asc => "ASC",
        Desc => "DESC",
    }
}

// ---------------------------------------------------------------------------
// DataBaseOperations — pre-computed f-string values
// ---------------------------------------------------------------------------

str_enum! {
    pub enum DataBaseOperations {
        Sup => ">",
        Inf => "<",
        Equals => "=",
        InfEquals => "<=",
        SupEquals => ">=",
    }
}

// ---------------------------------------------------------------------------
// RunDatabases
// ---------------------------------------------------------------------------

str_enum! {
    pub enum RunDatabases {
        History => "history",
        Live => "live",
        Backtesting => "backtesting",
        Optimizer => "optimizer",
        OptimizerRunsScheduleDb => "runs_schedule",
        RunDataDb => "run_data",
        PortfolioValueDb => "portfolio_value",
        HistoricalPortfolioValue => "historical_portfolio_value",
        OrdersDb => "orders",
        TradesDb => "trades",
        TransactionsDb => "transactions",
        Exchanges => "exchanges",
        Metadata => "metadata",
    }
}

// ---------------------------------------------------------------------------
// LogicalOperators
// ---------------------------------------------------------------------------

str_enum! {
    pub enum LogicalOperators {
        LowerThan => "lower_than",
        HigherThan => "higher_than",
        LowerOrEqualTo => "lower_or_equal_to",
        HigherOrEqualTo => "higher_or_equal_to",
        EqualTo => "equal_to",
        DifferentFrom => "different_from",
    }
}

// ---------------------------------------------------------------------------
// CommunityFeedAttrs
// ---------------------------------------------------------------------------

str_enum! {
    pub enum CommunityFeedAttrs {
        Id => "u",
        StreamId => "i",
        Value => "s",
        Version => "v",
        Timestamp => "d",
        ChannelType => "t",
    }
}

// ---------------------------------------------------------------------------
// CommunityChannelTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum CommunityChannelTypes {
        Configuration => "cfg",
        Signal => "t",
        Tradingview => "tv",
        Alert => "alert",
    }
}

// ---------------------------------------------------------------------------
// SignalBundlesAttrs
// ---------------------------------------------------------------------------

str_enum! {
    pub enum SignalBundlesAttrs {
        Identifier => "identifier",
        Signals => "signals",
        Version => "version",
    }
}

// ---------------------------------------------------------------------------
// SignalsAttrs
// ---------------------------------------------------------------------------

str_enum! {
    pub enum SignalsAttrs {
        Topic => "topic",
        Content => "content",
        Dependencies => "dependencies",
    }
}

// ---------------------------------------------------------------------------
// SignalDependenciesAttrs
// ---------------------------------------------------------------------------

str_enum! {
    pub enum SignalDependenciesAttrs {
        Dependency => "dependency",
    }
}

// ---------------------------------------------------------------------------
// InitializationEventExchangeTopics
// ---------------------------------------------------------------------------

str_enum! {
    pub enum InitializationEventExchangeTopics {
        Positions => "positions",
        Balance => "balance",
        Profitability => "profitability",
        Orders => "orders",
        Trades => "trades",
        Contracts => "contracts",
        Candles => "candles",
        Price => "price",
        OrderBook => "order_book",
        Funding => "funding",
        Markets => "markets",
    }
}

// ---------------------------------------------------------------------------
// UserInputTentacleTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum UserInputTentacleTypes {
        TradingMode => "trading_mode",
        Evaluator => "evaluator",
        Exchange => "exchange",
        BlockchainWallet => "blockchain_wallet",
        WebPlugin => "web_plugin",
        Automation => "automation",
        Undefined => "undefined",
    }
}

// ---------------------------------------------------------------------------
// UserInputTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum UserInputTypes {
        Int => "int",
        Float => "float",
        Boolean => "boolean",
        Options => "options",
        MultipleOptions => "multiple-options",
        Text => "text",
        Object => "object",
        ObjectArray => "object_array",
        StringArray => "string_array",
    }
}

// ---------------------------------------------------------------------------
// UserInputEditorOptionsTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum UserInputEditorOptionsTypes {
        Collapsed => "collapsed",
        DisableArrayAdd => "disable_array_add",
        DisableArrayDelete => "disable_array_delete",
        DisableArrayDeleteAllRows => "disable_array_delete_all_rows",
        DisableArrayDeleteLastRow => "disable_array_delete_last_row",
        DisableArrayReorder => "disable_array_reorder",
        DisableCollapse => "disable_collapse",
        DisableEditJson => "disable_edit_json",
        DisableProperties => "disable_properties",
        ArrayControlsTop => "array_controls_top",
        Enum => "enum",
        EnumTitles => "enum_titles",
        ExpandHeight => "expand_height",
        GridColumns => "grid_columns",
        Hidden => "hidden",
        InputHeight => "input_height",
        InputWidth => "input_width",
        RemoveEmptyProperties => "remove_empty_properties",
    }
}

// ---------------------------------------------------------------------------
// UserInputOtherSchemaValuesTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum UserInputOtherSchemaValuesTypes {
        Description => "description",
        Dependencies => "dependencies",
    }
}

// ---------------------------------------------------------------------------
// ProfileComplexity
// ---------------------------------------------------------------------------

int_enum! {
    pub enum ProfileComplexity {
        Easy => 1,
        Medium => 2,
        Difficult => 3,
    }
}

// ---------------------------------------------------------------------------
// ProfileRisk
// ---------------------------------------------------------------------------

int_enum! {
    pub enum ProfileRisk {
        Low => 1,
        Moderate => 2,
        High => 3,
    }
}

// ---------------------------------------------------------------------------
// ProfileType
// ---------------------------------------------------------------------------

str_enum! {
    pub enum ProfileType {
        Live => "live",
        Backtesting => "backtesting",
    }
}

// ---------------------------------------------------------------------------
// SignalHistoryTypes
// ---------------------------------------------------------------------------

str_enum! {
    pub enum SignalHistoryTypes {
        Gpt => "gpt",
    }
}

// ---------------------------------------------------------------------------
// StopReason
// ---------------------------------------------------------------------------

str_enum! {
    pub enum StopReason {
        MissingApiKeyTradingRights => "missing_api_key_trading_rights",
        InvalidExchangeCredentials => "invalid_exchange_credentials",
        StopConditionTriggered => "stop_condition_triggered",
        MissingMinimalFunds => "missing_minimal_funds",
        InvalidConfig => "invalid_config",
        Unknown => "unknown",
    }
}
