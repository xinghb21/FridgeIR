// bucket 文案 → 卡片标签样式。后端规则：
//   缺 0 → 马上能做 | 缺 1 → 再买 1 样 | 缺 2-3 → 还差几样 | 缺 4+ → 灵感参考
export function bucketClass(bucket: string): string {
  if (bucket.includes("马上")) return "bucket bucket-now";
  if (bucket.includes("再买")) return "bucket bucket-soon";
  if (bucket.includes("还差")) return "bucket bucket-some";
  return "bucket bucket-idea";
}

// bucket 对应的小图标，强化卡片标签的可读性。
export function bucketIcon(bucket: string): string {
  if (bucket.includes("马上")) return "✅";
  if (bucket.includes("再买")) return "🛒";
  if (bucket.includes("还差")) return "🧺";
  return "💡";
}
