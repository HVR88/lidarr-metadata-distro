using FluentValidation;
using NzbDrone.Core.Annotations;
using NzbDrone.Core.Extras.Metadata;
using NzbDrone.Core.ThingiProvider;
using NzbDrone.Core.Validation;

namespace LMBridgePlugin.Metadata.MetadataSourceOverride
{
    public class MetadataSourceOverrideSettingsValidator : AbstractValidator<MetadataSourceOverrideSettings>
    {
        public MetadataSourceOverrideSettingsValidator()
        {
            RuleFor(x => x.MetadataSource)
                .NotEmpty()
                .WithMessage("Metadata Source URL is required.")
                .IsValidUrl()
                .WithMessage("Metadata Source must be a valid HTTP or HTTPS URL.");
        }
    }

    public class MetadataSourceOverrideSettings : IProviderConfig
    {
        private static readonly MetadataSourceOverrideSettingsValidator Validator = new();

        public const string DefaultMetadataSource = "http://127.0.0.1:5001";

        [FieldDefinition(0, Label = "API URL", Type = FieldType.Url, Placeholder = DefaultMetadataSource, Section = MetadataSectionType.Metadata, HelpText = "HTTP://ADDRESS:PORT of your LM Bridge Instance")]
        public string MetadataSource { get; set; } = DefaultMetadataSource;

        public bool UseAtOwnRisk { get; set; } = true;

        public NzbDroneValidationResult Validate() => new(Validator.Validate(this));
    }
}
