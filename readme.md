Adding New Indicators in the Future
When you add a new indicator/strategy, follow these steps:

Add the indicator calculation in indicator_service.py
Add the indicator columns to the IndicatorValue model in models.py
Update _get_stored_indicator_values() in main.py to include the new fields
Update _get_latest_signal_from_stored() in main.py for signal extraction
Update the frontend mapping in both StrategyCard.jsx and ChartModal.jsx