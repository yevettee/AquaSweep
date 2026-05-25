"""Performance Evaluator for Fish Detection Pipeline.

Compares detection results with Isaac Sim ground truth.
Outputs metrics to CSV for offline analysis.

Metrics:
- Detection: Precision, Recall, F1, IoU
- Status: Accuracy for alive/suspicious classification
- Species: Accuracy for species classification
"""

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class DetectionMetrics:
    """Metrics for a single frame."""
    
    frame_id: int
    pool_id: int
    timestamp: str
    
    # Detection metrics
    gt_fish_count: int = 0
    pred_fish_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    mean_iou: float = 0.0
    
    # Status metrics (alive/suspicious)
    status_correct: int = 0
    status_total: int = 0
    
    # Species metrics
    species_correct: int = 0
    species_total: int = 0
    
    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)
    
    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)
    
    @property
    def f1_score(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)
    
    @property
    def status_accuracy(self) -> float:
        if self.status_total == 0:
            return 0.0
        return self.status_correct / self.status_total
    
    @property
    def species_accuracy(self) -> float:
        if self.species_total == 0:
            return 0.0
        return self.species_correct / self.species_total
    
    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "pool_id": self.pool_id,
            "timestamp": self.timestamp,
            "gt_fish_count": self.gt_fish_count,
            "pred_fish_count": self.pred_fish_count,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "mean_iou": self.mean_iou,
            "status_accuracy": self.status_accuracy,
            "species_accuracy": self.species_accuracy,
        }


class FishPerformanceEvaluator:
    """Evaluates fish detection performance against ground truth.
    
    Usage:
        evaluator = FishPerformanceEvaluator(output_dir="eval_results")
        
        for frame in frames:
            metrics = evaluator.evaluate_frame(
                pool_id=1,
                frame_id=frame.id,
                gt_fish=ground_truth,
                pred_fish=predictions,
            )
        
        evaluator.save_summary()
    """
    
    def __init__(
        self,
        output_dir: str = "eval_results",
        iou_threshold: float = 0.5,
    ):
        """Initialize evaluator.
        
        Args:
            output_dir: Directory for output CSV files
            iou_threshold: IoU threshold for matching GT with predictions
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.iou_threshold = iou_threshold
        self.metrics_history: List[DetectionMetrics] = []
        
        # Create CSV file
        self.csv_path = self.output_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file with headers."""
        headers = [
            "frame_id", "pool_id", "timestamp",
            "gt_fish_count", "pred_fish_count",
            "true_positives", "false_positives", "false_negatives",
            "precision", "recall", "f1_score", "mean_iou",
            "status_accuracy", "species_accuracy",
        ]
        
        with open(self.csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def evaluate_frame(
        self,
        pool_id: int,
        frame_id: int,
        gt_fish: List[dict],
        pred_fish: List[dict],
    ) -> DetectionMetrics:
        """Evaluate detection results for a single frame.
        
        Args:
            pool_id: Pool identifier
            frame_id: Frame number
            gt_fish: Ground truth fish list from Isaac Sim
                     Each dict: {"bbox_2d": (x,y,w,h), "species": str, "status": str}
            pred_fish: Predicted fish list from detector
                       Each dict: {"bbox": (x,y,w,h), "species": str, "status": str}
        
        Returns:
            DetectionMetrics for this frame
        """
        metrics = DetectionMetrics(
            frame_id=frame_id,
            pool_id=pool_id,
            timestamp=datetime.now().isoformat(),
            gt_fish_count=len(gt_fish),
            pred_fish_count=len(pred_fish),
        )
        
        # Match GT with predictions using IoU
        matched_gt = set()
        matched_pred = set()
        ious = []
        
        for i, gt in enumerate(gt_fish):
            gt_bbox = gt.get("bbox_2d") or gt.get("bbox")
            if gt_bbox is None:
                continue
            
            best_iou = 0.0
            best_pred_idx = -1
            
            for j, pred in enumerate(pred_fish):
                if j in matched_pred:
                    continue
                
                pred_bbox = pred.get("bbox")
                if pred_bbox is None:
                    continue
                
                iou = self._compute_iou(gt_bbox, pred_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_pred_idx = j
            
            if best_iou >= self.iou_threshold and best_pred_idx >= 0:
                matched_gt.add(i)
                matched_pred.add(best_pred_idx)
                ious.append(best_iou)
                metrics.true_positives += 1
                
                # Check species
                gt_species = gt.get("species", "unknown")
                pred_species = pred_fish[best_pred_idx].get("species", "unknown")
                metrics.species_total += 1
                if gt_species == pred_species:
                    metrics.species_correct += 1
                
                # Check status (alive/suspicious)
                gt_status = gt.get("status", "alive")
                pred_status = pred_fish[best_pred_idx].get("status", "alive")
                metrics.status_total += 1
                if gt_status == pred_status:
                    metrics.status_correct += 1
        
        # Count FP and FN
        metrics.false_negatives = len(gt_fish) - len(matched_gt)
        metrics.false_positives = len(pred_fish) - len(matched_pred)
        
        # Mean IoU for matched pairs
        if ious:
            metrics.mean_iou = float(np.mean(ious))
        
        # Save to history and CSV
        self.metrics_history.append(metrics)
        self._append_csv(metrics)
        
        return metrics
    
    def _compute_iou(
        self,
        bbox1: Tuple[int, int, int, int],
        bbox2: Tuple[int, int, int, int],
    ) -> float:
        """Compute IoU between two bboxes (x, y, w, h format)."""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Convert to x1, y1, x2, y2
        box1 = (x1, y1, x1 + w1, y1 + h1)
        box2 = (x2, y2, x2 + w2, y2 + h2)
        
        # Intersection
        xi1 = max(box1[0], box2[0])
        yi1 = max(box1[1], box2[1])
        xi2 = min(box1[2], box2[2])
        yi2 = min(box1[3], box2[3])
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        inter_area = (xi2 - xi1) * (yi2 - yi1)
        
        # Union
        area1 = w1 * h1
        area2 = w2 * h2
        union_area = area1 + area2 - inter_area
        
        if union_area <= 0:
            return 0.0
        
        return inter_area / union_area
    
    def _append_csv(self, metrics: DetectionMetrics):
        """Append metrics to CSV file."""
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                metrics.frame_id,
                metrics.pool_id,
                metrics.timestamp,
                metrics.gt_fish_count,
                metrics.pred_fish_count,
                metrics.true_positives,
                metrics.false_positives,
                metrics.false_negatives,
                f"{metrics.precision:.4f}",
                f"{metrics.recall:.4f}",
                f"{metrics.f1_score:.4f}",
                f"{metrics.mean_iou:.4f}",
                f"{metrics.status_accuracy:.4f}",
                f"{metrics.species_accuracy:.4f}",
            ])
    
    def get_summary(self) -> dict:
        """Get aggregated summary statistics."""
        if not self.metrics_history:
            return {}
        
        total_tp = sum(m.true_positives for m in self.metrics_history)
        total_fp = sum(m.false_positives for m in self.metrics_history)
        total_fn = sum(m.false_negatives for m in self.metrics_history)
        
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        mean_iou = np.mean([m.mean_iou for m in self.metrics_history if m.mean_iou > 0])
        
        status_correct = sum(m.status_correct for m in self.metrics_history)
        status_total = sum(m.status_total for m in self.metrics_history)
        status_acc = status_correct / status_total if status_total > 0 else 0.0
        
        species_correct = sum(m.species_correct for m in self.metrics_history)
        species_total = sum(m.species_total for m in self.metrics_history)
        species_acc = species_correct / species_total if species_total > 0 else 0.0
        
        return {
            "total_frames": len(self.metrics_history),
            "detection": {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "mean_iou": float(mean_iou) if not np.isnan(mean_iou) else 0.0,
            },
            "status_classification": {
                "accuracy": status_acc,
                "correct": status_correct,
                "total": status_total,
            },
            "species_classification": {
                "accuracy": species_acc,
                "correct": species_correct,
                "total": species_total,
            },
        }
    
    def save_summary(self) -> str:
        """Save summary to JSON file."""
        summary = self.get_summary()
        summary_path = self.output_dir / "summary.json"
        
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        return str(summary_path)
    
    def print_summary(self):
        """Print summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 50)
        print("  Fish Detection Performance Summary")
        print("=" * 50)
        print(f"\nTotal frames evaluated: {summary.get('total_frames', 0)}")
        
        det = summary.get("detection", {})
        print(f"\nDetection Metrics:")
        print(f"  Precision: {det.get('precision', 0):.4f}")
        print(f"  Recall:    {det.get('recall', 0):.4f}")
        print(f"  F1 Score:  {det.get('f1_score', 0):.4f}")
        print(f"  Mean IoU:  {det.get('mean_iou', 0):.4f}")
        
        status = summary.get("status_classification", {})
        print(f"\nStatus Classification (alive/suspicious):")
        print(f"  Accuracy: {status.get('accuracy', 0):.4f}")
        print(f"  Correct:  {status.get('correct', 0)} / {status.get('total', 0)}")
        
        species = summary.get("species_classification", {})
        print(f"\nSpecies Classification:")
        print(f"  Accuracy: {species.get('accuracy', 0):.4f}")
        print(f"  Correct:  {species.get('correct', 0)} / {species.get('total', 0)}")
        
        print("\n" + "=" * 50)
