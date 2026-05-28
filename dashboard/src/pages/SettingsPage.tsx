import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { useOnboarding } from "@/contexts/OnboardingContext"
import { useSettings } from "@/contexts/SettingsContext"

interface SettingRowProps {
  id: string
  title: string
  description: string
  checked: boolean
  onCheckedChange: (value: boolean) => void
}

function SettingRow({
  id,
  title,
  description,
  checked,
  onCheckedChange,
}: SettingRowProps) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-center justify-between gap-4 py-3"
    >
      <div>
        <p className="text-body font-medium">{title}</p>
        <p className="text-caption text-foreground-secondary">{description}</p>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
    </label>
  )
}

export function SettingsPage() {
  const {
    theme,
    setTheme,
    largeText,
    setLargeText,
    reduceMotion,
    setReduceMotion,
  } = useSettings()
  const { openOnboarding } = useOnboarding()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-h1 font-bold">설정</h1>
        <p className="mt-1 text-body text-foreground-secondary">
          화면을 보기 편하게 맞춰보세요.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-h3">화면</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          <SettingRow
            id="dark-mode"
            title="어두운 화면"
            description="눈부심을 줄이는 어두운 테마로 바꿔요."
            checked={theme === "dark"}
            onCheckedChange={(v) => setTheme(v ? "dark" : "light")}
          />
          <SettingRow
            id="large-text"
            title="글씨 크게"
            description="화면 전체를 크게 키워 더 잘 보이게 해요."
            checked={largeText}
            onCheckedChange={setLargeText}
          />
          <SettingRow
            id="reduce-motion"
            title="움직임 줄이기"
            description="깜빡임이나 흔들림 같은 애니메이션을 줄여요."
            checked={reduceMotion}
            onCheckedChange={setReduceMotion}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-h3">도움말</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4">
            <p className="text-body text-foreground-secondary">
              처음 사용법 안내를 다시 볼 수 있어요.
            </p>
            <Button
              variant="outline"
              className="h-btn shrink-0"
              onClick={openOnboarding}
            >
              사용법 다시 보기
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
