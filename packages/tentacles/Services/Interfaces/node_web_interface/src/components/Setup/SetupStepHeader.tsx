interface SetupStepHeaderProps {
  step?: number
  total?: number
  title: string
  subtitle: string
}

export function SetupStepHeader({
  step,
  total,
  title,
  subtitle,
}: SetupStepHeaderProps) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      {step !== undefined && total !== undefined && (
        <p className="text-xs text-muted-foreground">
          Step {step} / {total}
        </p>
      )}
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
    </div>
  )
}
