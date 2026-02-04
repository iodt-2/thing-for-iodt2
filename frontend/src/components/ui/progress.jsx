import * as React from "react"
import { cn } from "@/lib/utils"

const Progress = React.forwardRef(({ className, value = 0, ...props }, ref) => {
  // Ensure value is between 0 and 100
  const normalizedValue = Math.min(100, Math.max(0, value || 0));

  return (
    <div
      ref={ref}
      className={cn(
        "relative h-4 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700",
        className
      )}
      {...props}
    >
      <div
        className="h-full bg-blue-500 transition-all duration-300 ease-in-out"
        style={{ width: `${normalizedValue}%` }}
      />
    </div>
  );
});

Progress.displayName = "Progress";

export { Progress }