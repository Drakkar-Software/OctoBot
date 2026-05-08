// Per-exchange market fetching implementations.
// Each exchange calls request() with the correct versioned path and api section,
// since ccxt-rust's request() does NOT apply sign()-style version prefixes.
// Exchanges that use Binance-style base URLs (version embedded) work without this treatment.

use ccxt::exchange::{Exchange as CcxtExchange, Value as CcxtValue};
use serde_json::{json, Value};

pub type Markets = Vec<(String, Value)>;

fn to_json(v: CcxtValue) -> Option<Value> {
    match v {
        CcxtValue::Json(j) => Some(j),
        _ => None,
    }
}

fn req<'a>(
    exchange: &'a mut (dyn CcxtExchange + Send),
    path: &'a str,
    api: &'a str,
    params: Value,
) -> impl std::future::Future<Output = CcxtValue> + 'a {
    exchange.request(
        CcxtValue::from(path),
        CcxtValue::from(api),
        CcxtValue::from("GET"),
        CcxtValue::Json(params),
        CcxtValue::Undefined,
        CcxtValue::Undefined,
        CcxtValue::Undefined,
    )
}

fn make_market(id: &str, unified: &str, base: &str, quote: &str, active: bool) -> Value {
    json!({
        "id": id,
        "symbol": unified,
        "base": base,
        "quote": quote,
        "active": active,
    })
}

fn make_market_full(
    id: &str, unified: &str, base: &str, quote: &str, active: bool,
    price_prec: Option<f64>, amount_prec: Option<f64>,
    amount_min: Option<f64>, cost_min: Option<f64>,
    taker: Option<f64>, maker: Option<f64>,
    market_type: Option<&str>, contract_size: Option<f64>,
) -> Value {
    json!({
        "id": id,
        "symbol": unified,
        "base": base,
        "quote": quote,
        "active": active,
        "type": market_type,
        "contractSize": contract_size,
        "precision": { "price": price_prec, "amount": amount_prec },
        "limits": {
            "amount": { "min": amount_min },
            "cost": { "min": cost_min },
        },
        "taker": taker,
        "maker": maker,
    })
}

pub async fn fetch_markets(
    exchange: &mut (dyn CcxtExchange + Send),
    name: &str,
    is_future: bool,
) -> Markets {
    match name {
        // Binance family: base URL already includes version prefix (e.g. /api/v3)
        "binance" | "binanceus" => fetch_binance_family(exchange, "public", "exchangeInfo", false).await,
        "binanceusdm"           => fetch_binance_family(exchange, "fapiPublic", "exchangeInfo", true).await,
        "binancecoinm"          => fetch_binance_family(exchange, "dapiPublic", "exchangeInfo", true).await,
        // MEXC uses Binance-compatible exchangeInfo format
        "mexc"                  => fetch_binance_family(exchange, "spot", "api/v3/exchangeInfo", false).await,
        "okx" | "okxus"         => fetch_okx(exchange, is_future).await,
        "bybit"                 => fetch_bybit(exchange, is_future).await,
        "kucoin"                => fetch_kucoin(exchange).await,
        "kucoinfutures"         => fetch_kucoin_futures(exchange).await,
        "gate" | "gateio"       => fetch_gate(exchange, is_future).await,
        "htx" | "huobi"         => fetch_htx(exchange).await,
        "bitget"                => fetch_bitget(exchange, is_future).await,
        "coinbase" | "coinbaseadvanced" => fetch_coinbase(exchange).await,
        "poloniex"              => fetch_poloniex(exchange).await,
        "bingx"                 => fetch_bingx(exchange).await,
        "bitmart"               => fetch_bitmart(exchange).await,
        "coinex"                => fetch_coinex(exchange, is_future).await,
        "cryptocom"             => fetch_cryptocom(exchange, is_future).await,
        "lbank"                 => fetch_lbank(exchange).await,
        "phemex"                => fetch_phemex(exchange, is_future).await,
        "ascendex"              => fetch_ascendex(exchange).await,
        _ => vec![],
    }
}

// ---- Binance family (binance, binanceusdm, binancecoinm, binanceus, mexc) ----

async fn fetch_binance_family(
    exchange: &mut (dyn CcxtExchange + Send),
    api: &str,
    path: &str,
    is_futures: bool,
) -> Markets {
    let raw = exchange.request(
        CcxtValue::from(path),
        CcxtValue::from(api),
        CcxtValue::from("GET"),
        CcxtValue::Undefined,
        CcxtValue::Undefined,
        CcxtValue::Undefined,
        CcxtValue::Undefined,
    ).await;

    let resp = match to_json(raw) {
        Some(v) => v,
        None => return vec![],
    };
    let symbols = match resp["symbols"].as_array() {
        Some(a) => a.clone(),
        None => return vec![],
    };

    symbols.iter().filter_map(|s| {
        // For futures: only include perpetual contracts — delivery futures excluded intentionally.
        if is_futures && s["contractType"].as_str() != Some("PERPETUAL") {
            return None;
        }
        let id = s["symbol"].as_str()?;
        let base = s["baseAsset"].as_str()?;
        let quote = s["quoteAsset"].as_str()?;
        let active = s["status"].as_str() == Some("TRADING");
        let unified = if is_futures {
            // For COIN-M (dapiPublic), margin asset is the base; for USDM it's the quote.
            let settle = s["marginAsset"].as_str().unwrap_or(quote);
            format!("{}/{}:{}", base, quote, settle)
        } else {
            format!("{}/{}", base, quote)
        };

        // Extract precision from filters array
        let filters = s["filters"].as_array();
        let price_tick = filters.and_then(|fs| {
            fs.iter().find(|f| f["filterType"].as_str() == Some("PRICE_FILTER"))
                .and_then(|f| f["tickSize"].as_str())
                .and_then(|t| t.parse::<f64>().ok())
        });
        let lot_filter = filters.and_then(|fs| {
            fs.iter().find(|f| f["filterType"].as_str() == Some("LOT_SIZE")).cloned()
        });
        let amount_step = lot_filter.as_ref()
            .and_then(|f| f["stepSize"].as_str())
            .and_then(|s| s.parse::<f64>().ok());
        let amount_min = lot_filter.as_ref()
            .and_then(|f| f["minQty"].as_str())
            .and_then(|s| s.parse::<f64>().ok());
        let cost_min = filters.and_then(|fs| {
            fs.iter().find(|f| {
                let ft = f["filterType"].as_str().unwrap_or("");
                ft == "NOTIONAL" || ft == "MIN_NOTIONAL"
            })
            .and_then(|f| {
                f["minNotional"].as_str().or(f["notional"].as_str())
                    .and_then(|s| s.parse::<f64>().ok())
            })
        });

        let market_type = if is_futures { Some("swap") } else { Some("spot") };
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_tick, amount_step, amount_min, cost_min,
            None, None, market_type, None,
        )))
    }).collect()
}

// ---- OKX / OKXUS ----

async fn fetch_okx(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    let inst_type = if is_future { "SWAP" } else { "SPOT" };
    let raw = req(exchange, "api/v5/public/instruments", "rest",
        json!({"instType": inst_type})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["instId"].as_str()?;
        let base = s["baseCcy"].as_str()?;
        let quote = s["quoteCcy"].as_str()?;
        let settle = s["settleCcy"].as_str().unwrap_or(quote);
        let active = s["state"].as_str() == Some("live");
        let unified = if is_future {
            format!("{}/{}:{}", base, quote, settle)
        } else {
            format!("{}/{}", base, quote)
        };
        let price_prec = s["tickSz"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_prec = s["lotSz"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_min = s["minSz"].as_str().and_then(|t| t.parse::<f64>().ok());
        let contract_size = s["ctVal"].as_str().and_then(|t| t.parse::<f64>().ok());
        let market_type = if is_future { Some("swap") } else { Some("spot") };
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            None, None, market_type, contract_size,
        )))
    }).collect()
}

// ---- Bybit ----

async fn fetch_bybit(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    let category = if is_future { "linear" } else { "spot" };
    let raw = req(exchange, "v5/market/instruments-info", "public",
        json!({"category": category})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let list = match resp["result"]["list"].as_array() { Some(a) => a.clone(), None => return vec![] };

    list.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let base = s["baseCoin"].as_str()?;
        let quote = s["quoteCoin"].as_str()?;
        let settle = s["settleCoin"].as_str().unwrap_or(quote);
        let active = s["status"].as_str() == Some("Trading");
        let unified = if is_future {
            format!("{}/{}:{}", base, quote, settle)
        } else {
            format!("{}/{}", base, quote)
        };
        let price_prec = s["priceFilter"]["tickSize"].as_str()
            .and_then(|t| t.parse::<f64>().ok());
        let amount_prec = s["lotSizeFilter"]["basePrecision"].as_str()
            .or(s["lotSizeFilter"]["qtyStep"].as_str())
            .and_then(|t| t.parse::<f64>().ok());
        let amount_min = s["lotSizeFilter"]["minOrderQty"].as_str()
            .and_then(|t| t.parse::<f64>().ok());
        let market_type = if is_future { Some("swap") } else { Some("spot") };
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            None, None, market_type, None,
        )))
    }).collect()
}

// ---- KuCoin ----

async fn fetch_kucoin(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "api/v1/symbols", "public", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let base = s["baseCurrency"].as_str()?;
        let quote = s["quoteCurrency"].as_str()?;
        let active = s["enableTrading"].as_bool().unwrap_or(false);
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["priceIncrement"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_prec = s["baseIncrement"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_min = s["baseMinSize"].as_str().and_then(|t| t.parse::<f64>().ok());
        let cost_min = s["quoteMinSize"].as_str().and_then(|t| t.parse::<f64>().ok());
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, cost_min,
            None, None, Some("spot"), None,
        )))
    }).collect()
}

// ---- KuCoin Futures ----

async fn fetch_kucoin_futures(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "api/v1/contracts/active", "public", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        // Include only perpetual contracts (type FFWCSX = crypto perpetual)
        if s["type"].as_str() != Some("FFWCSX") {
            return None;
        }
        let id = s["symbol"].as_str()?;
        let base = s["baseCurrency"].as_str()?;
        let quote = s["quoteCurrency"].as_str()?;
        let settle = s["settleCurrency"].as_str().unwrap_or(quote);
        let active = !s["isDecommissioned"].as_bool().unwrap_or(true);
        let unified = format!("{}/{}:{}", base, quote, settle);
        let price_prec = s["tickSize"].as_f64();
        let amount_prec = s["lotSize"].as_f64();
        let contract_size = s["multiplier"].as_f64();
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, None, None,
            None, None, Some("swap"), contract_size,
        )))
    }).collect()
}

// ---- Gate.io ----

async fn fetch_gate(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    if is_future {
        // Gate USDT-settled perpetuals
        let raw = req(exchange, "futures/usdt/contracts", "public", json!({})).await;
        let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
        let data = match resp.as_array() { Some(a) => a.clone(), None => return vec![] };
        return data.iter().filter_map(|s| {
            let id = s["name"].as_str()?;
            // Gate futures name format: "BTC_USDT"
            let parts: Vec<&str> = id.splitn(2, '_').collect();
            if parts.len() != 2 { return None; }
            let base = parts[0];
            let settle = parts[1];
            let active = !s["in_delisting"].as_bool().unwrap_or(false);
            let unified = format!("{}/{}:{}", base, settle, settle);
            let price_prec = s["order_price_round"].as_str()
                .and_then(|t| t.parse::<f64>().ok());
            Some((unified.clone(), make_market_full(
                id, &unified, base, settle, active,
                price_prec, None, None, None,
                s["taker_fee_rate"].as_str().and_then(|t| t.parse().ok()),
                s["maker_fee_rate"].as_str().and_then(|t| t.parse().ok()),
                Some("swap"), s["quanto_multiplier"].as_str().and_then(|t| t.parse().ok()),
            )))
        }).collect();
    }
    let raw = req(exchange, "spot/currency_pairs", "public", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp.as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["id"].as_str()?;
        let base = s["base"].as_str()?;
        let quote = s["quote"].as_str()?;
        let active = s["trade_status"].as_str() == Some("tradable");
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["precision"].as_u64().map(|p| 10f64.powi(-(p as i32)));
        let amount_prec = s["amount_precision"].as_u64().map(|p| 10f64.powi(-(p as i32)));
        let amount_min = s["min_base_amount"].as_str().and_then(|t| t.parse::<f64>().ok());
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            s["fee"].as_str().and_then(|t| t.parse().ok()),
            s["fee"].as_str().and_then(|t| t.parse().ok()),
            Some("spot"), None,
        )))
    }).collect()
}

// ---- HTX / Huobi ----

async fn fetch_htx(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "v1/common/symbols", "public", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let base_raw = s["base-currency"].as_str()?;
        let quote_raw = s["quote-currency"].as_str()?;
        let base = base_raw.to_uppercase();
        let quote = quote_raw.to_uppercase();
        let active = s["state"].as_str() == Some("online");
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["price-precision"].as_u64().map(|p| 10f64.powi(-(p as i32)));
        let amount_prec = s["amount-precision"].as_u64().map(|p| 10f64.powi(-(p as i32)));
        let amount_min = s["min-order-amt"].as_f64();
        let cost_min = s["min-order-value"].as_f64();
        Some((unified.clone(), make_market_full(
            id, &unified, &base, &quote, active,
            price_prec, amount_prec, amount_min, cost_min,
            None, None, Some("spot"), None,
        )))
    }).collect()
}

// ---- Bitget ----

async fn fetch_bitget(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    if is_future {
        let raw = req(exchange, "api/v2/mix/market/contracts", "mix",
            json!({"productType": "USDT-FUTURES"})).await;
        let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
        let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };
        return data.iter().filter_map(|s| {
            let id = s["symbol"].as_str()?;
            let base = s["baseCoin"].as_str()?;
            let quote = s["quoteCoin"].as_str()?;
            let settle = s["marginCoin"].as_str().unwrap_or(quote);
            let active = s["symbolStatus"].as_str() == Some("normal");
            let unified = format!("{}/{}:{}", base, quote, settle);
            let price_prec = s["priceEndStep"].as_str().and_then(|t| t.parse::<f64>().ok());
            let amount_prec = s["sizeMultiplier"].as_str().and_then(|t| t.parse::<f64>().ok());
            let contract_size = s["sizeMultiplier"].as_str().and_then(|t| t.parse::<f64>().ok());
            Some((unified.clone(), make_market_full(
                id, &unified, base, quote, active,
                price_prec, amount_prec, None, None,
                s["takerFeeRate"].as_str().and_then(|t| t.parse().ok()),
                s["makerFeeRate"].as_str().and_then(|t| t.parse().ok()),
                Some("swap"), contract_size,
            )))
        }).collect();
    }
    let raw = req(exchange, "api/v2/spot/public/symbols", "spot", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let base = s["baseCoin"].as_str()?;
        let quote = s["quoteCoin"].as_str()?;
        let active = s["status"].as_str() == Some("online");
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["pricePrecision"].as_str().and_then(|t| t.parse::<f64>().ok())
            .map(|p| 10f64.powi(-(p as i32)));
        let amount_prec = s["quantityPrecision"].as_str().and_then(|t| t.parse::<f64>().ok())
            .map(|p| 10f64.powi(-(p as i32)));
        let amount_min = s["minTradeAmount"].as_str().and_then(|t| t.parse::<f64>().ok());
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            s["takerFeeRate"].as_str().and_then(|t| t.parse().ok()),
            s["makerFeeRate"].as_str().and_then(|t| t.parse().ok()),
            Some("spot"), None,
        )))
    }).collect()
}

// ---- Coinbase Advanced ----

async fn fetch_coinbase(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "api/v3/brokerage/products", "rest", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let products = match resp["products"].as_array() { Some(a) => a.clone(), None => return vec![] };

    products.iter().filter_map(|s| {
        if s["product_type"].as_str() != Some("SPOT") { return None; }
        let id = s["product_id"].as_str()?;
        let base = s["base_currency_id"].as_str()?;
        let quote = s["quote_currency_id"].as_str()?;
        let active = s["status"].as_str() == Some("online");
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["price_increment"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_prec = s["base_increment"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_min = s["base_min_size"].as_str().and_then(|t| t.parse::<f64>().ok());
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            None, None, Some("spot"), None,
        )))
    }).collect()
}

// ---- Poloniex ----

async fn fetch_poloniex(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "markets", "spot", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp.as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let base = s["baseCurrencyName"].as_str()?;
        let quote = s["quoteCurrencyName"].as_str()?;
        let active = s["state"].as_str() == Some("NORMAL");
        let unified = format!("{}/{}", base, quote);
        Some((unified.clone(), make_market(id, &unified, base, quote, active)))
    }).collect()
}

// ---- BingX ----

async fn fetch_bingx(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "spot/v1/common/symbols", "spot", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"]["symbols"].as_array()
        .or(resp["data"].as_array()) {
        Some(a) => a.clone(),
        None => return vec![],
    };

    data.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let active = s["apiStateSell"].as_bool().unwrap_or(true)
            && s["apiStateBuy"].as_bool().unwrap_or(true);
        // BingX symbol format: "BTC-USDT"
        let parts: Vec<&str> = id.splitn(2, '-').collect();
        if parts.len() != 2 { return None; }
        let (base, quote) = (parts[0], parts[1]);
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["tickSize"].as_str()
            .and_then(|t| t.parse::<f64>().ok())
            .or(s["pricePrecision"].as_u64().map(|p| 10f64.powi(-(p as i32))));
        let amount_prec = s["stepSize"].as_str()
            .and_then(|t| t.parse::<f64>().ok())
            .or(s["quantityPrecision"].as_u64().map(|p| 10f64.powi(-(p as i32))));
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, None, None,
            None, None, Some("spot"), None,
        )))
    }).collect()
}

// ---- BitMart ----

async fn fetch_bitmart(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "spot/v1/symbols/details", "spot", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"]["symbols"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["symbol"].as_str()?;
        let base = s["base_currency"].as_str()?;
        let quote = s["quote_currency"].as_str()?;
        let active = s["trade_status"].as_str() == Some("trading");
        let unified = format!("{}/{}", base, quote);
        let price_prec = s["price_min_precision"].as_u64().map(|p| 10f64.powi(-(p as i32)));
        let amount_prec = s["quote_increment"].as_str()
            .and_then(|t| t.parse::<f64>().ok());
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, None, None,
            None, None, Some("spot"), None,
        )))
    }).collect()
}

// ---- CoinEx ----

async fn fetch_coinex(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    let path = if is_future { "v2/futures/market" } else { "v2/spot/market" };
    let raw = req(exchange, path, "public", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let id = s["market"].as_str()?;
        let base = s["base_ccy"].as_str()?;
        let quote = s["quote_ccy"].as_str()?;
        let active = true; // CoinEx API only returns active markets
        let unified = if is_future {
            let settle = s["settle_ccy"].as_str().unwrap_or(quote);
            format!("{}/{}:{}", base, quote, settle)
        } else {
            format!("{}/{}", base, quote)
        };
        let taker = s["taker_fee_rate"].as_str().and_then(|t| t.parse::<f64>().ok());
        let maker = s["maker_fee_rate"].as_str().and_then(|t| t.parse::<f64>().ok());
        let market_type = if is_future { Some("swap") } else { Some("spot") };
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            None, None, None, None, taker, maker, market_type, None,
        )))
    }).collect()
}

// ---- Crypto.com ----

async fn fetch_cryptocom(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    let raw = req(exchange, "public/get-instruments", "v1", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["result"]["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let inst_type = s["inst_type"].as_str().unwrap_or("");
        let is_perp = inst_type == "PERPETUAL_SWAP" || inst_type == "FUTURE";
        if is_future != is_perp { return None; }
        if !is_future && inst_type != "CCY_PAIR" { return None; }

        let id = s["symbol"].as_str().or(s["instrument_name"].as_str())?;
        let base = s["base_ccy"].as_str()?;
        let quote = s["quote_ccy"].as_str()?;
        let active = s["tradable"].as_bool().unwrap_or(true);
        let unified = if is_future {
            format!("{}/{}:{}", base, quote, quote)
        } else {
            format!("{}/{}", base, quote)
        };
        let price_prec = s["price_tick_size"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_prec = s["quantity_tick_size"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_min = s["min_quantity"].as_str().and_then(|t| t.parse::<f64>().ok());
        let market_type = if is_future { Some("swap") } else { Some("spot") };
        Some((unified.clone(), make_market_full(
            id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            None, None, market_type, None,
        )))
    }).collect()
}

// ---- LBank ----

async fn fetch_lbank(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "v2/currencyPairs.do", "rest", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp.as_array()
        .or(resp["data"].as_array()) {
        Some(a) => a.clone(),
        None => return vec![],
    };

    data.iter().filter_map(|s| {
        let id = s.as_str()?;
        // LBank format: "btc_usdt"
        let parts: Vec<&str> = id.splitn(2, '_').collect();
        if parts.len() != 2 { return None; }
        let base = parts[0].to_uppercase();
        let quote = parts[1].to_uppercase();
        let unified = format!("{}/{}", base, quote);
        Some((unified.clone(), make_market(id, &unified, &base, &quote, true)))
    }).collect()
}

// ---- Phemex ----

async fn fetch_phemex(exchange: &mut (dyn CcxtExchange + Send), is_future: bool) -> Markets {
    // Phemex: urls.api.public = "https://{hostname}/exchange/public"
    // So request("cfg/v2/products", "public", GET) → https://api.phemex.com/exchange/public/cfg/v2/products
    let raw = req(exchange, "cfg/v2/products", "public", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let products = match resp["data"]["products"].as_array() { Some(a) => a.clone(), None => return vec![] };

    products.iter().filter_map(|s| {
        let prod_type = s["type"].as_str().unwrap_or("");
        let is_perp = prod_type == "Perpetual" || prod_type == "PerpetualV2";
        if is_future != is_perp { return None; }
        if !is_future && prod_type != "Spot" { return None; }

        let id = s["symbol"].as_str()?;
        let base = s["baseCurrency"].as_str()?;
        let quote = s["quoteCurrency"].as_str()?;
        let active = s["status"].as_str().map(|st| st != "Closed").unwrap_or(true);
        let unified = if is_future {
            let settle = s["settlementCurrency"].as_str().unwrap_or(quote);
            format!("{}/{}:{}", base, quote, settle)
        } else {
            format!("{}/{}", base, quote)
        };
        Some((unified.clone(), make_market(id, &unified, base, quote, active)))
    }).collect()
}

// ---- AscendEx ----

async fn fetch_ascendex(exchange: &mut (dyn CcxtExchange + Send)) -> Markets {
    let raw = req(exchange, "api/pro/v1/products", "rest", json!({})).await;
    let resp = match to_json(raw) { Some(v) => v, None => return vec![] };
    let data = match resp["data"].as_array() { Some(a) => a.clone(), None => return vec![] };

    data.iter().filter_map(|s| {
        let symbol = s["symbol"].as_str()?;
        let base = s["baseAsset"].as_str()?;
        let quote = s["quoteAsset"].as_str()?;
        let active = s["status"].as_str().map(|st| st == "Normal").unwrap_or(true);
        // AscendEx symbol is already in "BTC/USDT" format
        let unified = symbol.to_string();
        let id = symbol.replace('/', "-");
        let price_prec = s["tickSize"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_prec = s["lotSize"].as_str().and_then(|t| t.parse::<f64>().ok());
        let amount_min = s["minQty"].as_str().and_then(|t| t.parse::<f64>().ok());
        Some((unified.clone(), make_market_full(
            &id, &unified, base, quote, active,
            price_prec, amount_prec, amount_min, None,
            None, None, Some("spot"), None,
        )))
    }).collect()
}
