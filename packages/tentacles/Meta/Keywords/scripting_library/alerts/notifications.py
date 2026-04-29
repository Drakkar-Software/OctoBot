import octobot_services.api as services_api
import octobot_services.enums as services_enum


async def send_alert(title, alert_content,
                     level: services_enum.NotificationLevel = services_enum.NotificationLevel.INFO,
                     sound=services_enum.NotificationSound.NO_SOUND):
    await services_api.send_notification(services_api.create_notification(alert_content, title=title, level=level,
                                                                          markdown_text=alert_content,
                                                                          sound=sound,
                                                                          category=services_enum.
                                                                          NotificationCategory.TRADING_SCRIPT_ALERTS))
