use octobot_commons::symbols::symbol::Symbol;

// --- Fixtures ---

fn spot_symbol() -> Symbol {
    Symbol::new("BTC/USDT")
}

fn perpetual_future_symbol() -> Symbol {
    Symbol::new("BTC/USDT:BTC")
}

fn future_symbol() -> Symbol {
    Symbol::new("ETH/USDT:USDT-210625")
}

fn option_symbol() -> Symbol {
    Symbol::new("ETH/USDT:USDT-211225-40000-C")
}

fn put_option_symbol() -> Symbol {
    Symbol::new("BTC/USDT:BTC-211225-60000-P")
}

// --- Parsing tests ---

#[test]
fn test_parse_spot_symbol() {
    let s = spot_symbol();
    assert_eq!(s.base.as_deref(), Some("BTC"));
    assert_eq!(s.quote.as_deref(), Some("USDT"));
    assert_eq!(s.settlement_asset.as_deref(), Some(""));
    assert_eq!(s.identifier.as_deref(), Some(""));
    assert_eq!(s.strike_price.as_deref(), Some(""));
    assert_eq!(s.option_type, None);
}

#[test]
fn test_parse_perpetual_future_symbol() {
    let s = perpetual_future_symbol();
    assert_eq!(s.base.as_deref(), Some("BTC"));
    assert_eq!(s.quote.as_deref(), Some("USDT"));
    assert_eq!(s.settlement_asset.as_deref(), Some("BTC"));
    assert_eq!(s.strike_price.as_deref(), Some(""));
    assert_eq!(s.option_type, None);
}

#[test]
fn test_parse_future_symbol() {
    let s = future_symbol();
    assert_eq!(s.base.as_deref(), Some("ETH"));
    assert_eq!(s.quote.as_deref(), Some("USDT"));
    assert_eq!(s.settlement_asset.as_deref(), Some("USDT"));
    assert_eq!(s.identifier.as_deref(), Some("210625"));
    assert_eq!(s.strike_price.as_deref(), Some(""));
    assert_eq!(s.option_type, None);
}

#[test]
fn test_parse_option_symbol() {
    let s = option_symbol();
    assert_eq!(s.base.as_deref(), Some("ETH"));
    assert_eq!(s.quote.as_deref(), Some("USDT"));
    assert_eq!(s.settlement_asset.as_deref(), Some("USDT"));
    assert_eq!(s.identifier.as_deref(), Some("211225"));
    assert_eq!(s.strike_price.as_deref(), Some("40000"));
    assert_eq!(s.option_type.as_deref(), Some("C"));
}

// --- base_and_quote ---

#[test]
fn test_base_and_quote() {
    let spot = spot_symbol();
    assert_eq!(spot.base_and_quote(), (Some("BTC"), Some("USDT")));

    let option = option_symbol();
    assert_eq!(option.base_and_quote(), (Some("ETH"), Some("USDT")));
}

// --- is_linear / is_inverse ---

#[test]
fn test_is_linear() {
    assert!(spot_symbol().is_linear());
    assert!(!perpetual_future_symbol().is_linear());
    assert!(option_symbol().is_linear());
}

#[test]
fn test_is_inverse() {
    assert!(!spot_symbol().is_inverse());
    assert!(perpetual_future_symbol().is_inverse());
    assert!(!option_symbol().is_inverse());
}

// --- merged_str_symbol ---

#[test]
fn test_merged_str_symbol_with_full_option() {
    let call = Symbol::new("ETH/USDT:USDT-211225-40000-C");
    assert_eq!(
        call.merged_str_symbol(None, None, None),
        "ETH/USDT:USDT-211225-40000-C"
    );

    let put = Symbol::new("BTC/USDT:BTC-211225-60000-P");
    assert_eq!(
        put.merged_str_symbol(None, None, None),
        "BTC/USDT:BTC-211225-60000-P"
    );
}

// --- is_put_option / is_call_option ---

#[test]
fn test_is_put_option() {
    let put = put_option_symbol();
    assert!(put.is_put_option());
    assert!(!put.is_call_option());
}

#[test]
fn test_is_call_option() {
    let call = option_symbol();
    assert!(call.is_call_option());
    assert!(!call.is_put_option());
}

#[test]
fn test_is_put_and_call_option_with_non_option_symbols() {
    let spot = spot_symbol();
    assert!(!spot.is_put_option());
    assert!(!spot.is_call_option());

    let perpetual = perpetual_future_symbol();
    assert!(!perpetual.is_put_option());
    assert!(!perpetual.is_call_option());

    let future = future_symbol();
    assert!(!future.is_put_option());
    assert!(!future.is_call_option());
}

// --- does_expire ---

#[test]
fn test_does_expire() {
    assert!(!spot_symbol().does_expire());
    assert!(!perpetual_future_symbol().does_expire());
    assert!(future_symbol().does_expire());
    assert!(option_symbol().does_expire());
    assert!(put_option_symbol().does_expire());
}

// --- equality ---

#[test]
fn test_eq() {
    assert_eq!(Symbol::new("BTC/USDT"), Symbol::new("BTC/USDT"));
    assert_ne!(Symbol::new("BTC/USDT"), Symbol::new("BTC/USD"));
    assert_ne!(
        Symbol::new("BTC/USDT"),
        Symbol::new("ETH/USDT:USDT-211225-40000-C")
    );
    assert_eq!(
        Symbol::new("ETH/USDT:USDT-211225-40000-C"),
        Symbol::new("ETH/USDT:USDT-211225-40000-C")
    );
    assert_ne!(
        Symbol::new("ETH/USDT:USDT-211225-40000-C"),
        Symbol::new("ETH/USDT:USDT-211225-40000-P")
    );
}
