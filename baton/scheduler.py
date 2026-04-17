from apscheduler.schedulers.background import BackgroundScheduler
from baton.learner import SlackLearner


class LearningScheduler:
    def __init__(self, learner: SlackLearner):
        self.learner = learner
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    def start(self) -> None:
        """매주 월요일 오전 6시 자동 학습 등록 후 시작"""
        self.scheduler.add_job(
            self.learner.learn_all_channels,
            trigger="cron",
            day_of_week="mon",
            hour=6,
            minute=0,
            id="weekly_learning",
            replace_existing=True
        )
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
