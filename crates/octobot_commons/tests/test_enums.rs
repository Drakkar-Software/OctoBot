use octobot_commons::enums::*;

// ---------------------------------------------------------------------------
// TimeFrames
// ---------------------------------------------------------------------------

#[test]
fn test_time_frames_value() {
    assert_eq!(TimeFrames::OneMinute.value(), "1m");
    assert_eq!(TimeFrames::OneHour.value(), "1h");
    assert_eq!(TimeFrames::OneDay.value(), "1d");
}

#[test]
fn test_time_frames_from_value() {
    assert_eq!(TimeFrames::from_value("1m"), Some(TimeFrames::OneMinute));
    assert_eq!(TimeFrames::from_value("1h"), Some(TimeFrames::OneHour));
    assert_eq!(TimeFrames::from_value("1d"), Some(TimeFrames::OneDay));
    assert_eq!(TimeFrames::from_value("invalid"), None);
}

#[test]
fn test_time_frames_variants() {
    let variants = TimeFrames::variants();
    assert!(variants.contains(&TimeFrames::OneMinute));
    assert!(variants.contains(&TimeFrames::OneHour));
    assert!(variants.contains(&TimeFrames::OneDay));
    assert!(variants.contains(&TimeFrames::OneWeek));
}

#[test]
fn test_time_frames_display() {
    assert_eq!(format!("{}", TimeFrames::OneMinute), "1m");
    assert_eq!(format!("{}", TimeFrames::OneHour), "1h");
    assert_eq!(format!("{}", TimeFrames::OneDay), "1d");
}

// ---------------------------------------------------------------------------
// time_frames_minutes
// ---------------------------------------------------------------------------

#[test]
fn test_time_frames_minutes() {
    assert_eq!(time_frames_minutes(TimeFrames::OneMinute), 1);
    assert_eq!(time_frames_minutes(TimeFrames::OneHour), 60);
    assert_eq!(time_frames_minutes(TimeFrames::OneDay), 1440);
}

// ---------------------------------------------------------------------------
// PriceIndexes (int_enum)
// ---------------------------------------------------------------------------

#[test]
fn test_price_indexes_value() {
    assert_eq!(PriceIndexes::IndPriceClose.value(), 4);
    assert_eq!(PriceIndexes::IndPriceTime.value(), 0);
    assert_eq!(PriceIndexes::IndPriceVol.value(), 5);
}

#[test]
fn test_price_indexes_from_value() {
    assert_eq!(
        PriceIndexes::from_value(4),
        Some(PriceIndexes::IndPriceClose)
    );
    assert_eq!(
        PriceIndexes::from_value(0),
        Some(PriceIndexes::IndPriceTime)
    );
    assert_eq!(PriceIndexes::from_value(99), None);
}

// ---------------------------------------------------------------------------
// OptionTypes
// ---------------------------------------------------------------------------

#[test]
fn test_option_types() {
    assert_eq!(OptionTypes::Put.value(), "P");
    assert_eq!(OptionTypes::Call.value(), "C");
    assert_eq!(OptionTypes::from_value("P"), Some(OptionTypes::Put));
    assert_eq!(OptionTypes::from_value("C"), Some(OptionTypes::Call));
    assert_eq!(OptionTypes::from_value("X"), None);
}

// ---------------------------------------------------------------------------
// MarkdownFormat
// ---------------------------------------------------------------------------

#[test]
fn test_markdown_format_italic() {
    assert_eq!(MarkdownFormat::Italic.str_value(), Some("_"));
    assert_eq!(MarkdownFormat::Italic.int_value(), None);
}

#[test]
fn test_markdown_format_ignore() {
    assert_eq!(MarkdownFormat::Ignore.str_value(), None);
    assert_eq!(MarkdownFormat::Ignore.int_value(), Some(1));
}

#[test]
fn test_markdown_format_none() {
    assert_eq!(MarkdownFormat::None.str_value(), None);
    assert_eq!(MarkdownFormat::None.int_value(), Some(0));
}

// ---------------------------------------------------------------------------
// LogicalOperators
// ---------------------------------------------------------------------------

#[test]
fn test_logical_operators_all_six() {
    assert_eq!(LogicalOperators::LowerThan.value(), "lower_than");
    assert_eq!(LogicalOperators::HigherThan.value(), "higher_than");
    assert_eq!(
        LogicalOperators::LowerOrEqualTo.value(),
        "lower_or_equal_to"
    );
    assert_eq!(
        LogicalOperators::HigherOrEqualTo.value(),
        "higher_or_equal_to"
    );
    assert_eq!(LogicalOperators::EqualTo.value(), "equal_to");
    assert_eq!(LogicalOperators::DifferentFrom.value(), "different_from");
    assert_eq!(LogicalOperators::variants().len(), 6);
}

// ---------------------------------------------------------------------------
// DataBaseOperations
// ---------------------------------------------------------------------------

#[test]
fn test_database_operations() {
    assert_eq!(DataBaseOperations::InfEquals.value(), "<=");
    assert_eq!(DataBaseOperations::SupEquals.value(), ">=");
    assert_eq!(DataBaseOperations::Sup.value(), ">");
    assert_eq!(DataBaseOperations::Inf.value(), "<");
    assert_eq!(DataBaseOperations::Equals.value(), "=");
}
