from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from movies.models import Rating
from movies.recommender.mf import train_mf_sgd
from movies.recommender.model_storage import get_model_meta, save_model


class Command(BaseCommand):
    help = "预训练矩阵分解模型并保存到磁盘"

    def add_arguments(self, parser):
        parser.add_argument("--k", type=int, default=20, help="隐因子维度")
        parser.add_argument("--steps", type=int, default=50, help="迭代次数")
        parser.add_argument("--lr", type=float, default=0.01, help="学习率")
        parser.add_argument("--reg", type=float, default=0.02, help="正则化系数")
        parser.add_argument("--force", action="store_true", help="强制重新训练")

    def handle(self, *args, **options):
        k = options["k"]
        steps = options["steps"]
        lr = options["lr"]
        reg = options["reg"]
        force = options["force"]

        meta = get_model_meta()
        if meta and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"模型已存在 (版本: {meta['version']}, 更新时间: {meta['updated_at']})"
                )
            )
            self.stdout.write("使用 --force 参数强制重新训练")
            return

        rating_rows = list(Rating.objects.values_list("user_id", "movie_id", "score"))
        
        if not rating_rows:
            self.stdout.write(self.style.ERROR("没有评分数据，无法训练模型"))
            return

        self.stdout.write(f"加载了 {len(rating_rows)} 条评分记录")
        self.stdout.write(f"开始训练模型 (k={k}, steps={steps}, lr={lr}, reg={reg})...")

        start_time = time.time()
        
        model = train_mf_sgd(
            rating_rows=[(int(u), int(m), float(s)) for (u, m, s) in rating_rows],
            k=k,
            steps=steps,
            lr=lr,
            reg=reg,
        )

        training_time = time.time() - start_time

        if model is None:
            self.stdout.write(self.style.ERROR("模型训练失败"))
            return

        save_model(model, training_info={
            "k": k,
            "steps": steps,
            "lr": lr,
            "reg": reg,
            "n_ratings": len(rating_rows),
            "training_time_seconds": round(training_time, 2),
        })

        self.stdout.write(
            self.style.SUCCESS(
                f"模型训练完成！耗时 {training_time:.2f} 秒\n"
                f"用户数: {len(model.user_ids)}, 电影数: {len(model.movie_ids)}"
            )
        )
