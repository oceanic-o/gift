import * as React from "react";
import { X, Check, ChevronsUpDown } from "lucide-react";
import { cn } from "./utils";
import { Badge } from "./badge";

interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function MultiSelect({ options, selected, onChange, placeholder = "Select...", className }: MultiSelectProps) {
  const [open, setOpen] = React.useState(false);
  const [openUpward, setOpenUpward] = React.useState(false);
  const [menuMaxHeight, setMenuMaxHeight] = React.useState(256);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const VISIBLE_BADGES = 6;

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  React.useEffect(() => {
    if (!open || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const viewportH = window.innerHeight || 0;
    const spaceBelow = viewportH - rect.bottom - 12;
    const spaceAbove = rect.top - 12;
    const shouldOpenUpward = spaceBelow < 220 && spaceAbove > spaceBelow;
    setOpenUpward(shouldOpenUpward);
    const bestSpace = shouldOpenUpward ? spaceAbove : spaceBelow;
    setMenuMaxHeight(Math.max(160, Math.min(320, Math.floor(bestSpace))));
  }, [open, options.length]);

  const handleUnselect = (item: string) => {
    onChange(selected.filter((i) => i !== item));
  };

  const toggleOption = (option: string) => {
    onChange(
      selected.includes(option)
        ? selected.filter((item) => item !== option)
        : [...selected, option]
    );
  };

  const visibleSelected = selected.slice(0, VISIBLE_BADGES);
  const remainingCount = Math.max(0, selected.length - VISIBLE_BADGES);

  return (
    <div className={cn("relative w-full", className)} ref={containerRef}>
      <div 
        onClick={() => setOpen(!open)}
        className="flex min-h-12 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
      >
        <div className="flex max-h-24 overflow-y-auto flex-wrap gap-1 items-center font-normal flex-1 pr-1">
          {selected.length === 0 ? (
            <span className="text-muted-foreground text-sm">{placeholder}</span>
          ) : (
            visibleSelected.map((item) => (
              <Badge variant="secondary" key={item} className="mr-1 mb-1" onClick={(e) => { e.stopPropagation(); handleUnselect(item); }}>
                {item}
                <button
                  className="ml-1 ring-offset-background rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleUnselect(item);
                  }}
                >
                  <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                </button>
              </Badge>
            ))
          )}
          {remainingCount > 0 && (
            <Badge variant="outline" className="mr-1 mb-1">
              +{remainingCount} more
            </Badge>
          )}
        </div>
        <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50 ml-2" />
      </div>

      {open && (
        <div
          className={cn(
            "absolute left-0 right-0 z-[9999] rounded-xl border-2 border-rose-200 bg-white text-popover-foreground shadow-2xl outline-none min-w-[200px]",
            openUpward ? "bottom-full mb-2" : "top-full mt-2",
          )}
        >
          <div className="overflow-auto p-1 py-2 bg-white rounded-xl" style={{ maxHeight: `${menuMaxHeight}px` }}>
            {!options || options.length === 0 ? (
              <div className="py-6 px-2 text-center text-sm text-muted-foreground">Loading or no results found.</div>
            ) : (
              options.map((option) => (
                <div
                  key={option}
                  onClick={() => toggleOption(option)}
                  className="relative flex w-full select-none items-center rounded-md py-2.5 pl-3 pr-8 text-sm outline-none hover:bg-rose-50 hover:text-rose-900 cursor-pointer transition-colors"
                >
                  <Check
                    className={cn(
                      "mr-3 h-4 w-4 text-rose-600 transition-opacity",
                      selected.includes(option) ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {option}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
