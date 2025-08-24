"""
Gold Monitor Report Generator

This module generates HTML reports for gold price monitoring,
integrating with the existing TrendRadar report structure.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .gold_price_collector import GoldPriceData
from .price_analyzer import PriceAlert, PriceTrend, TrendDirection

@dataclass
class GoldReportData:
    """Gold monitoring report data structure"""
    summaries: Dict[str, Dict]
    alerts: List[PriceAlert]
    trends: Dict[str, PriceTrend]
    timestamp: datetime
    
class GoldReportGenerator:
    """Generates HTML reports for gold price monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_gold_section_html(self, report_data: GoldReportData) -> str:
        """Generate the gold monitoring section HTML"""
        
        # Generate summary cards
        summary_cards = self._generate_summary_cards(report_data.summaries)
        
        # Generate price charts
        price_charts = self._generate_price_charts(report_data.summaries)
        
        # Generate alerts section
        alerts_section = self._generate_alerts_section(report_data.alerts)
        
        # Generate trends section
        trends_section = self._generate_trends_section(report_data.trends)
        
        # Combine all sections
        gold_section = f"""
        <!-- Gold Price Monitoring Section -->
        <div class="gold-monitor-section">
            <div class="gold-header">
                <div class="gold-title">
                    <span class="gold-icon">💰</span>
                    <h2>黄金价格监控</h2>
                </div>
                <div class="gold-timestamp">
                    更新时间: {report_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
            
            {summary_cards}
            {price_charts}
            {alerts_section}
            {trends_section}
        </div>
        """
        
        return gold_section
    
    def _generate_summary_cards(self, summaries: Dict[str, Dict]) -> str:
        """Generate price summary cards"""
        if not summaries:
            return '<div class="gold-no-data">暂无黄金价格数据</div>'
        
        cards_html = '<div class="gold-summary-cards">'
        
        for symbol, summary in summaries.items():
            current_price = summary.get('current_price', 0)
            currency = summary.get('currency', 'USD')
            
            # Get latest change
            changes = summary.get('changes', {})
            latest_change = 0
            change_period = '1h'
            if '1h' in changes:
                latest_change = changes['1h']['change_percent']
            elif '6h' in changes:
                latest_change = changes['6h']['change_percent']
                change_period = '6h'
            elif '24h' in changes:
                latest_change = changes['24h']['change_percent']
                change_period = '24h'
            
            # Determine trend direction and color
            trend_class = 'neutral'
            trend_icon = '➡️'
            if latest_change > 0:
                trend_class = 'positive'
                trend_icon = '📈'
            elif latest_change < 0:
                trend_class = 'negative'
                trend_icon = '📉'
            
            # Get trend info
            trend = summary.get('trend', {})
            trend_direction = trend.get('direction', 'unknown')
            volatility = trend.get('volatility', 0)
            
            # Get alerts count
            alerts_count = len(summary.get('alerts', []))
            alerts_badge = f'<span class="alerts-badge">{alerts_count}</span>' if alerts_count > 0 else ''
            
            card_html = f"""
            <div class="gold-card {trend_class}">
                <div class="card-header">
                    <div class="symbol-info">
                        <span class="symbol-name">{symbol}</span>
                        {alerts_badge}
                    </div>
                    <span class="trend-icon">{trend_icon}</span>
                </div>
                <div class="card-body">
                    <div class="price-info">
                        <span class="current-price">{current_price:.2f}</span>
                        <span class="currency">{currency}</span>
                    </div>
                    <div class="change-info">
                        <span class="change-value {trend_class}">{latest_change:+.2f}%</span>
                        <span class="change-period">({change_period})</span>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="trend-info">
                        <span class="trend-label">趋势:</span>
                        <span class="trend-value">{self._translate_trend(trend_direction)}</span>
                    </div>
                    <div class="volatility-info">
                        <span class="volatility-label">波动:</span>
                        <span class="volatility-value">{volatility:.1f}%</span>
                    </div>
                </div>
            </div>
            """
            cards_html += card_html
        
        cards_html += '</div>'
        return cards_html
    
    def _generate_price_charts(self, summaries: Dict[str, Dict]) -> str:
        """Generate price charts section"""
        if not summaries:
            return ''
        
        # Generate chart data for JavaScript
        chart_data = {}
        for symbol, summary in summaries.items():
            changes = summary.get('changes', {})
            chart_data[symbol] = {
                'current_price': summary.get('current_price', 0),
                'currency': summary.get('currency', 'USD'),
                'changes': changes
            }
        
        chart_data_json = json.dumps(chart_data, ensure_ascii=False)
        
        charts_html = f"""
        <div class="gold-charts-section">
            <h3>价格走势图表</h3>
            <div class="charts-container">
                <canvas id="goldPriceChart" width="400" height="200"></canvas>
            </div>
            <script>
                // Chart data
                const goldChartData = {chart_data_json};
                
                // Initialize chart when DOM is loaded
                document.addEventListener('DOMContentLoaded', function() {{
                    initializeGoldChart(goldChartData);
                }});
            </script>
        </div>
        """
        
        return charts_html
    
    def _generate_alerts_section(self, alerts: List[PriceAlert]) -> str:
        """Generate alerts section"""
        if not alerts:
            return '<div class="gold-alerts-empty">✅ 当前无价格预警</div>'
        
        alerts_html = '<div class="gold-alerts-section">'
        alerts_html += '<h3>🚨 价格预警</h3>'
        alerts_html += '<div class="alerts-list">'
        
        # Sort alerts by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_alerts = sorted(alerts, key=lambda x: severity_order.get(x.severity, 4))
        
        for alert in sorted_alerts:
            severity_emoji = {
                'critical': '🚨',
                'high': '🔴',
                'medium': '🟠',
                'low': '🟡'
            }.get(alert.severity, '⚠️')
            
            severity_class = f'alert-{alert.severity}'
            
            alert_html = f"""
            <div class="alert-item {severity_class}">
                <div class="alert-header">
                    <span class="alert-icon">{severity_emoji}</span>
                    <span class="alert-symbol">{alert.symbol}</span>
                    <span class="alert-severity">{alert.severity.upper()}</span>
                    <span class="alert-time">{alert.timestamp.strftime('%H:%M')}</span>
                </div>
                <div class="alert-body">
                    <div class="alert-message">{alert.message}</div>
                    <div class="alert-details">
                        <span class="price-change">{alert.change_percent:+.2f}%</span>
                        <span class="price-current">${alert.current_price:.2f}</span>
                    </div>
                </div>
            </div>
            """
            alerts_html += alert_html
        
        alerts_html += '</div></div>'
        return alerts_html
    
    def _generate_trends_section(self, trends: Dict[str, PriceTrend]) -> str:
        """Generate trends analysis section"""
        if not trends:
            return ''
        
        trends_html = '<div class="gold-trends-section">'
        trends_html += '<h3>📊 趋势分析</h3>'
        trends_html += '<div class="trends-list">'
        
        for symbol, trend in trends.items():
            trend_emoji = {
                'rising': '📈',
                'falling': '📉',
                'stable': '➡️',
                'volatile': '🌊'
            }.get(trend.direction.value, '❓')
            
            strength_desc = self._get_strength_description(trend.strength)
            trend_class = f'trend-{trend.direction.value}'
            
            trend_html = f"""
            <div class="trend-item {trend_class}">
                <div class="trend-header">
                    <span class="trend-icon">{trend_emoji}</span>
                    <span class="trend-symbol">{symbol}</span>
                    <span class="trend-direction">{self._translate_trend(trend.direction.value)}</span>
                </div>
                <div class="trend-body">
                    <div class="trend-metrics">
                        <div class="metric">
                            <span class="metric-label">强度:</span>
                            <span class="metric-value">{strength_desc}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">平均变动:</span>
                            <span class="metric-value">{trend.average_change_percent:+.2f}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">波动率:</span>
                            <span class="metric-value">{trend.volatility:.2f}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">持续时间:</span>
                            <span class="metric-value">{trend.duration_hours:.1f}小时</span>
                        </div>
                    </div>
                </div>
            </div>
            """
            trends_html += trend_html
        
        trends_html += '</div></div>'
        return trends_html
    
    def _translate_trend(self, trend_direction: str) -> str:
        """Translate trend direction to Chinese"""
        translations = {
            'rising': '上涨',
            'falling': '下跌',
            'stable': '稳定',
            'volatile': '波动',
            'unknown': '未知'
        }
        return translations.get(trend_direction, trend_direction)
    
    def _get_strength_description(self, strength: float) -> str:
        """Get strength description in Chinese"""
        if strength >= 0.8:
            return '很强'
        elif strength >= 0.6:
            return '强'
        elif strength >= 0.4:
            return '中等'
        elif strength >= 0.2:
            return '弱'
        else:
            return '很弱'
    
    def generate_gold_css(self) -> str:
        """Generate CSS styles for gold monitoring section"""
        return """
        /* Gold Price Monitoring Styles */
        .gold-monitor-section {
            margin-top: 40px;
            padding-top: 24px;
            border-top: 2px solid #f0f0f0;
        }
        
        .gold-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e5e5e5;
        }
        
        .gold-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .gold-icon {
            font-size: 24px;
        }
        
        .gold-title h2 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .gold-timestamp {
            color: #666;
            font-size: 13px;
        }
        
        .gold-summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        
        .gold-card {
            background: white;
            border: 1px solid #e5e5e5;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s ease;
        }
        
        .gold-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        .gold-card.positive {
            border-left: 4px solid #10b981;
        }
        
        .gold-card.negative {
            border-left: 4px solid #ef4444;
        }
        
        .gold-card.neutral {
            border-left: 4px solid #6b7280;
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .symbol-info {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .symbol-name {
            font-weight: 600;
            font-size: 16px;
            color: #1a1a1a;
        }
        
        .alerts-badge {
            background: #ef4444;
            color: white;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 10px;
            min-width: 16px;
            text-align: center;
        }
        
        .trend-icon {
            font-size: 20px;
        }
        
        .card-body {
            margin-bottom: 16px;
        }
        
        .price-info {
            display: flex;
            align-items: baseline;
            gap: 4px;
            margin-bottom: 8px;
        }
        
        .current-price {
            font-size: 24px;
            font-weight: 700;
            color: #1a1a1a;
        }
        
        .currency {
            font-size: 14px;
            color: #666;
            font-weight: 500;
        }
        
        .change-info {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .change-value {
            font-weight: 600;
            font-size: 14px;
        }
        
        .change-value.positive {
            color: #10b981;
        }
        
        .change-value.negative {
            color: #ef4444;
        }
        
        .change-value.neutral {
            color: #6b7280;
        }
        
        .change-period {
            font-size: 12px;
            color: #999;
        }
        
        .card-footer {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #666;
        }
        
        .trend-label, .volatility-label {
            font-weight: 500;
        }
        
        .trend-value, .volatility-value {
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .gold-charts-section {
            margin-bottom: 32px;
        }
        
        .gold-charts-section h3 {
            margin: 0 0 16px 0;
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .charts-container {
            background: white;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 20px;
        }
        
        .gold-alerts-section, .gold-trends-section {
            margin-bottom: 32px;
        }
        
        .gold-alerts-section h3, .gold-trends-section h3 {
            margin: 0 0 16px 0;
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .gold-alerts-empty {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            color: #166534;
            font-weight: 500;
        }
        
        .alerts-list, .trends-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .alert-item {
            background: white;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 16px;
        }
        
        .alert-item.alert-critical {
            border-left: 4px solid #dc2626;
            background: #fef2f2;
        }
        
        .alert-item.alert-high {
            border-left: 4px solid #ea580c;
            background: #fff7ed;
        }
        
        .alert-item.alert-medium {
            border-left: 4px solid #d97706;
            background: #fffbeb;
        }
        
        .alert-item.alert-low {
            border-left: 4px solid #eab308;
            background: #fefce8;
        }
        
        .alert-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .alert-icon {
            font-size: 16px;
        }
        
        .alert-symbol {
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .alert-severity {
            background: rgba(0,0,0,0.1);
            color: #1a1a1a;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        .alert-time {
            margin-left: auto;
            font-size: 12px;
            color: #666;
        }
        
        .alert-message {
            font-size: 14px;
            color: #1a1a1a;
            margin-bottom: 8px;
        }
        
        .alert-details {
            display: flex;
            gap: 12px;
            font-size: 12px;
        }
        
        .price-change {
            font-weight: 600;
        }
        
        .price-current {
            color: #666;
        }
        
        .trend-item {
            background: white;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 16px;
        }
        
        .trend-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .trend-symbol {
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .trend-direction {
            background: rgba(0,0,0,0.1);
            color: #1a1a1a;
            font-size: 12px;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        .trend-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
        }
        
        .metric {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .metric-label {
            font-size: 11px;
            color: #666;
            font-weight: 500;
        }
        
        .metric-value {
            font-size: 13px;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .gold-no-data {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 32px;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }
        
        @media (max-width: 768px) {
            .gold-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
            
            .gold-summary-cards {
                grid-template-columns: 1fr;
            }
            
            .card-footer {
                flex-direction: column;
                gap: 4px;
            }
            
            .trend-metrics {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        """
    
    def generate_chart_js(self) -> str:
        """Generate JavaScript for price charts"""
        return """
        // Gold Price Chart JavaScript
        function initializeGoldChart(chartData) {
            const canvas = document.getElementById('goldPriceChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            // Simple chart implementation (can be replaced with Chart.js)
            drawSimpleChart(ctx, chartData);
        }
        
        function drawSimpleChart(ctx, data) {
            const canvas = ctx.canvas;
            const width = canvas.width;
            const height = canvas.height;
            
            // Clear canvas
            ctx.clearRect(0, 0, width, height);
            
            // Chart settings
            const padding = 40;
            const chartWidth = width - 2 * padding;
            const chartHeight = height - 2 * padding;
            
            // Draw background
            ctx.fillStyle = '#f9fafb';
            ctx.fillRect(padding, padding, chartWidth, chartHeight);
            
            // Draw border
            ctx.strokeStyle = '#e5e7eb';
            ctx.lineWidth = 1;
            ctx.strokeRect(padding, padding, chartWidth, chartHeight);
            
            // Draw title
            ctx.fillStyle = '#1f2937';
            ctx.font = '14px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('黄金价格走势', width / 2, 25);
            
            // Draw symbols and prices
            const symbols = Object.keys(data);
            if (symbols.length === 0) {
                ctx.fillStyle = '#6b7280';
                ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillText('暂无数据', width / 2, height / 2);
                return;
            }
            
            const barWidth = chartWidth / symbols.length * 0.6;
            const barSpacing = chartWidth / symbols.length;
            
            symbols.forEach((symbol, index) => {
                const symbolData = data[symbol];
                const price = symbolData.current_price;
                const currency = symbolData.currency;
                
                // Calculate bar position
                const x = padding + index * barSpacing + (barSpacing - barWidth) / 2;
                const barHeight = (price / 3000) * chartHeight * 0.8; // Normalize to max 3000
                const y = padding + chartHeight - barHeight;
                
                // Draw bar
                ctx.fillStyle = '#3b82f6';
                ctx.fillRect(x, y, barWidth, barHeight);
                
                // Draw price label
                ctx.fillStyle = '#1f2937';
                ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(`${price.toFixed(0)}`, x + barWidth / 2, y - 5);
                
                // Draw symbol label
                ctx.fillText(symbol, x + barWidth / 2, padding + chartHeight + 15);
            });
        }
        """

# Example usage
if __name__ == "__main__":
    # Example usage
    generator = GoldReportGenerator()
    
    # Example data
    from datetime import datetime
    
    example_summaries = {
        "XAUUSD": {
            "current_price": 2050.75,
            "currency": "USD",
            "changes": {
                "1h": {"change_percent": 1.25}
            },
            "trend": {
                "direction": "rising",
                "volatility": 2.5
            },
            "alerts": []
        }
    }
    
    example_report_data = GoldReportData(
        summaries=example_summaries,
        alerts=[],
        trends={},
        timestamp=datetime.now()
    )
    
    # Generate HTML section
    html_section = generator.generate_gold_section_html(example_report_data)
    print("Generated HTML section length:", len(html_section))
    
    # Generate CSS
    css_styles = generator.generate_gold_css()
    print("Generated CSS length:", len(css_styles))
    
    # Generate JavaScript
    js_code = generator.generate_chart_js()
    print("Generated JavaScript length:", len(js_code))